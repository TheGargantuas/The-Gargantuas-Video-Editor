# Integrazione Remote Upscaling con Google Colab

Questa guida spiega come usare la GPU di Google Colab come servizio remoto di
upscaling per un'altra applicazione.

Il Video Editor viene avviato su Colab, Gradio genera un URL pubblico e l'altra
applicazione invia a quell'URL un'immagine o un singolo frame insieme al modello
RealESRGAN da usare. Il risultato viene restituito come immagine upscalata.

## Indice

- [Architettura](#architettura)
- [Avvio del server su Colab](#avvio-del-server-su-colab)
- [Integrazione consigliata in Python](#integrazione-consigliata-in-python)
- [Esempi d'uso](#esempi-duso)
- [Contratto REST](#contratto-rest)
- [Modelli disponibili](#modelli-disponibili)
- [Configurazione](#configurazione)
- [Gestione degli errori](#gestione-degli-errori)
- [Prestazioni e integrazione video](#prestazioni-e-integrazione-video)
- [Checklist](#checklist)

## Architettura

```text
Applicazione locale
    │
    │ immagine/frame + modello + token opzionale
    ▼
URL pubblico Gradio su Colab
    │
    ├─ decodifica base64
    ├─ selezione automatica CUDA
    ├─ caricamento/cache del modello RealESRGAN
    └─ upscaling sulla GPU
    │
    ▼
Immagine upscalata base64
    │
    └─ PIL Image, frame OpenCV oppure file locale
```

L'endpoint pubblico è denominato `upscale_image`. Gradio usa una coda: il client
esegue una richiesta `POST` per creare il job e legge il risultato tramite una
seconda richiesta `GET` in formato SSE. La classe `RemoteUpscaleClient` gestisce
automaticamente entrambi i passaggi.

Le chiamate vengono elaborate una alla volta. Questo impedisce che richieste
con modelli diversi modifichino contemporaneamente lo stato dell'upsampler e
riduce il rischio di esaurire la VRAM del runtime Colab.

## Avvio del server su Colab

### 1. Abilitare la GPU

In Colab selezionare:

```text
Runtime → Change runtime type → T4 GPU
```

### 2. Avviare il progetto

Eseguire il setup descritto in [`colab/COLAB_SETUP.md`](../colab/COLAB_SETUP.md)
oppure il contenuto di `colab/colab_notebook_setup.py`.

Il setup imposta:

```python
%env GRADIO_SHARE=true
```

La cella finale avvia `main.py`. Nell'output apparirà un URL simile a:

```text
https://abc123.gradio.live
```

La cella deve rimanere in esecuzione. L'URL smette di funzionare quando il
runtime Colab viene arrestato, si disconnette oppure la cella viene interrotta.

### 3. Proteggere l'endpoint

Il link Gradio è pubblico. Prima di avviare `main.py` è consigliato configurare
un token lungo e casuale:

```python
%env UPSCALE_API_TOKEN=sostituisci-con-un-token-lungo-e-casuale
```

Il client deve inviare lo stesso valore. Se `UPSCALE_API_TOKEN` non è impostato
sul server, l'endpoint accetta richieste senza token.

Il controllo del token è applicativo: in caso di token errato la chiamata HTTP
può terminare correttamente, ma il risultato contiene `ok: false`.

### 4. Verificare che l'API sia esposta

Aprire nel browser:

```text
https://abc123.gradio.live/gradio_api/info
```

Tra i named endpoint deve essere presente `/upscale_image` con tre parametri:

1. `image_payload`
2. `model_name`
3. `api_token`

## Integrazione consigliata in Python

L'applicazione client non deve installare Gradio, PyTorch o RealESRGAN. Queste
dipendenze rimangono sul Colab. Il client richiede soltanto:

```bash
pip install requests Pillow numpy
```

Il modulo client richiede Python 3.10 o successivo.

### Copiare il client

Copiare [`utils/remote_upscale.py`](../utils/remote_upscale.py) nel progetto che
deve usare il servizio. Per esempio:

```text
altra-app/
├── integrations/
│   └── remote_upscale.py
└── main.py
```

Il modulo è autonomo e usa esclusivamente `requests`, `Pillow` e `numpy` oltre
alla libreria standard.

### Configurazione locale

È consigliato leggere URL e token dall'ambiente:

```bash
export GRADIO_URL="https://abc123.gradio.live"
export UPSCALE_API_TOKEN="sostituisci-con-un-token-lungo-e-casuale"
```

Creare una sola istanza del client e riutilizzarla. In questo modo viene
riutilizzata anche la sessione HTTP:

```python
import os

from integrations.remote_upscale import RemoteUpscaleClient


remote_upscaler = RemoteUpscaleClient(
    os.environ["GRADIO_URL"],
    token=os.getenv("UPSCALE_API_TOKEN"),
    timeout=900,
)
```

`timeout` indica il numero massimo di secondi di attesa dello stream del
risultato. Il valore predefinito è 900 secondi.

## Esempi d'uso

### Salvare direttamente su file

```python
output_path = remote_upscaler.upscale_to_file(
    image="input/frame.png",
    model="RealESRGAN_x4plus",
    output_path="output/frame_upscaled.png",
)

print(output_path)
```

Il tipo restituito è `pathlib.Path`. Il formato di salvataggio viene determinato
dall'estensione di `output_path`.

### Ottenere una `PIL.Image`

`upscale_image()` accetta un percorso, bytes, una `PIL.Image` oppure un array
NumPy RGB:

```python
from PIL import Image


source = Image.open("input/foto.jpg")
result = remote_upscaler.upscale_image(source, "RealESRGAN_x2plus")
result.save("output/foto_upscaled.jpg")
```

### Inviare bytes

```python
with open("input/foto.webp", "rb") as image_file:
    image_bytes = image_file.read()

result = remote_upscaler.upscale_image(
    image_bytes,
    "RealESRNet_x4plus",
)
```

### Inviare un frame OpenCV

`upscale_frame()` è pensato per OpenCV: accetta un array NumPy BGR e restituisce
un array NumPy BGR.

```python
import cv2


frame = cv2.imread("input/frame.png")
if frame is None:
    raise RuntimeError("Impossibile leggere il frame")

upscaled_frame = remote_upscaler.upscale_frame(
    frame,
    "RealESRGAN_x4plus",
)

cv2.imwrite("output/frame_upscaled.png", upscaled_frame)
```

Non è necessario convertire manualmente BGR → RGB: lo fa il client prima
dell'invio e riconverte il risultato in BGR.

### Leggere anche i metadati

Il metodo `request()` restituisce l'intera risposta del server:

```python
response = remote_upscaler.request(
    "input/frame.png",
    "RealESRGAN_x4plus_anime_6B",
)

print(response["model"])
print(response["scale"])
print(response["device"])
print(response["info"])
```

Dopo una chiamata eseguita con successo, gli stessi dati sono disponibili in
`remote_upscaler.last_response`.

### Uso in un'applicazione asincrona

`requests` è sincrono. In FastAPI, aiohttp, una GUI asincrona o un event loop è
opportuno eseguire la chiamata in un thread:

```python
import asyncio


async def upscale_without_blocking(frame, model):
    return await asyncio.to_thread(
        remote_upscaler.upscale_frame,
        frame,
        model,
    )
```

Questo evita di bloccare l'event loop locale; il server Colab continuerà comunque
a processare i job uno alla volta.

### Client da riga di comando

All'interno di questo repository è disponibile anche
[`remote_upscale_client.py`](../remote_upscale_client.py):

```bash
python remote_upscale_client.py \
  --url https://abc123.gradio.live \
  --input ./frame.png \
  --output ./frame_upscaled.png \
  --model RealESRGAN_x4plus \
  --token sostituisci-con-un-token-lungo-e-casuale
```

`--url` e `--token` possono essere omessi se sono già definite le variabili
`GRADIO_URL` e `UPSCALE_API_TOKEN`.

## Contratto REST

Questa sezione serve per integrare client non Python o implementare un client
personalizzato.

### Endpoint

Con le versioni recenti di Gradio:

```text
POST /gradio_api/call/upscale_image
GET  /gradio_api/call/upscale_image/{event_id}
```

Con versioni Gradio precedenti il prefisso può essere:

```text
POST /call/upscale_image
GET  /call/upscale_image/{event_id}
```

`RemoteUpscaleClient` prova automaticamente entrambe le varianti.

### Payload della POST

La proprietà `data` è una lista posizionale con esattamente tre valori:

```json
{
  "data": [
    "data:image/png;base64,iVBORw0KGgoAAA...",
    "RealESRGAN_x4plus",
    "token-opzionale"
  ]
}
```

| Posizione | Nome | Tipo | Descrizione |
|---:|---|---|---|
| 0 | `image_payload` | stringa | Data URL base64 oppure base64 puro |
| 1 | `model_name` | stringa | Nome esatto di uno dei modelli supportati |
| 2 | `api_token` | stringa | Token configurato sul server oppure stringa vuota |

La risposta della POST contiene l'identificatore del job:

```json
{
  "event_id": "0123456789abcdef"
}
```

### Lettura del risultato

Eseguire la GET usando `event_id`. La risposta è uno stream SSE e può contenere:

- `event: heartbeat`: il server è ancora collegato;
- `event: generating`: il job è in elaborazione;
- `event: complete`: il risultato è pronto;
- `event: error`: il job Gradio è fallito.

Il `data` dell'evento `complete` è una lista JSON. Il primo elemento è la
risposta dell'upscaler.

### Risposta di successo

```json
{
  "ok": true,
  "image": "data:image/png;base64,iVBORw0KGgoAAA...",
  "model": "RealESRGAN_x4plus",
  "scale": 4,
  "device": "GPU (CUDA)",
  "info": "✓ Image upscaled successfully..."
}
```

| Campo | Tipo | Descrizione |
|---|---|---|
| `ok` | booleano | `true` se l'upscaling è riuscito |
| `image` | stringa | Immagine risultante come data URL base64 |
| `model` | stringa | Modello effettivamente usato |
| `scale` | intero | Fattore 2 oppure 4 |
| `device` | stringa | Device selezionato dal server |
| `info` | stringa | Dimensioni e informazioni di elaborazione |

### Risposta applicativa di errore

```json
{
  "ok": false,
  "error": "Invalid or missing UPSCALE_API_TOKEN"
}
```

Per un modello sconosciuto è presente anche `available_models`:

```json
{
  "ok": false,
  "error": "Unsupported model: modello-errato",
  "available_models": [
    "RealESRGAN_x4plus",
    "RealESRGAN_x2plus",
    "RealESRNet_x4plus",
    "RealESRGAN_x4plus_anime_6B"
  ]
}
```

### Esempio REST essenziale

```python
import base64
import json
import requests


base_url = "https://abc123.gradio.live"

with open("frame.png", "rb") as image_file:
    encoded = base64.b64encode(image_file.read()).decode("ascii")

submission = requests.post(
    f"{base_url}/gradio_api/call/upscale_image",
    json={
        "data": [
            f"data:image/png;base64,{encoded}",
            "RealESRGAN_x4plus",
            "token-opzionale",
        ]
    },
    timeout=30,
)
submission.raise_for_status()
event_id = submission.json()["event_id"]

with requests.get(
    f"{base_url}/gradio_api/call/upscale_image/{event_id}",
    stream=True,
    timeout=(10, 900),
) as stream:
    stream.raise_for_status()
    for line in stream.iter_lines(decode_unicode=True):
        if line.startswith("data:"):
            data = json.loads(line.removeprefix("data:").strip())
            # L'ultima data associata a `event: complete` contiene il risultato.
            print(data)
```

Per produzione è preferibile usare il client incluso, che associa correttamente
ogni riga `data` al relativo tipo di evento e gestisce errori e compatibilità.

## Modelli disponibili

| Modello | Scala | Uso consigliato |
|---|---:|---|
| `RealESRGAN_x4plus` | 4× | Uso generale, miglior equilibrio qualità/prestazioni |
| `RealESRGAN_x2plus` | 2× | Elaborazione più leggera e output meno grande |
| `RealESRNet_x4plus` | 4× | Risultato più pulito e meno aggressivo |
| `RealESRGAN_x4plus_anime_6B` | 4× | Anime, illustrazioni e contenuti cartoon |

Il nome deve corrispondere esattamente a uno dei valori della tabella.

Il primo utilizzo di un modello può essere più lento perché il server scarica i
pesi RealESRGAN. Le richieste successive con lo stesso modello e device riusano
l'upsampler già caricato in memoria.

## Configurazione

### Variabili sul server Colab

| Variabile | Default | Descrizione |
|---|---|---|
| `GRADIO_SHARE` | `false` nel progetto | Abilita il tunnel pubblico Gradio; il setup Colab la imposta a `true` |
| `UPSCALE_API_TOKEN` | vuota | Se valorizzata, richiede lo stesso token nel payload |
| `UPSCALE_API_MAX_INPUT_MB` | `25` | Dimensione massima dei bytes dell'immagine decodificata |

Se `UPSCALE_API_MAX_INPUT_MB` contiene un valore non valido o non positivo, il
server ripristina automaticamente il limite a 25 MB.

### Variabili consigliate nell'altra applicazione

| Variabile | Obbligatoria | Descrizione |
|---|---|---|
| `GRADIO_URL` | sì | URL pubblico del runtime Colab attualmente attivo |
| `UPSCALE_API_TOKEN` | solo se configurata sul server | Token condiviso con il Colab |

Non salvare il token nel repository. Usare environment variables, secret manager
o il sistema di configurazione sicura dell'applicazione.

### Selezione del device

Il client non invia il device. Il server seleziona automaticamente il primo
disponibile in questo ordine:

1. `GPU (CUDA)`
2. `MPS (Apple Silicon)`
3. `CPU`

Su un runtime Colab configurato correttamente la risposta deve quindi mostrare
`"device": "GPU (CUDA)"`.

## Gestione degli errori

Il client solleva `RemoteUpscaleError` quando il server restituisce `ok: false`,
quando il protocollo Gradio fallisce o quando la risposta non contiene
un'immagine valida.

```python
from integrations.remote_upscale import RemoteUpscaleError


try:
    result = remote_upscaler.upscale_image(
        "input/frame.png",
        "RealESRGAN_x4plus",
    )
except RemoteUpscaleError as exc:
    logger.error("Upscaling remoto fallito: %s", exc)
```

| Errore | Causa probabile | Azione |
|---|---|---|
| `Invalid or missing UPSCALE_API_TOKEN` | Token mancante o diverso | Sincronizzare il secret tra client e Colab |
| `Unsupported model` | Nome modello errato | Usare uno dei quattro nomi supportati |
| `The image payload is not valid base64` | Payload corrotto | Usare il client o verificare la codifica |
| `The input image exceeds ... MB` | Input oltre il limite | Ridurre l'immagine o aumentare il limite sul server |
| `Endpoint 'upscale_image' not found` | Colab usa una versione precedente del codice | Aggiornare il repository sul Colab e riavviare |
| Timeout o errore di connessione | Runtime fermo, URL scaduto o rete assente | Recuperare il nuovo URL e ricreare il client |
| CUDA out of memory | Frame/output troppo grande | Usare il modello 2× o ridurre le dimensioni di input |

Non ripetere automaticamente una richiesta dopo aver ricevuto `event_id` senza
prima verificare il risultato: il job potrebbe essere ancora in esecuzione e un
retry creerebbe un secondo upscaling identico.

## Prestazioni e integrazione video

L'endpoint elabora immagini singole. Per un video, l'altra applicazione deve:

1. leggere un frame;
2. inviarlo con `upscale_frame()`;
3. scrivere il frame risultante nel video di output;
4. ripetere mantenendo l'ordine originale;
5. gestire separatamente l'audio.

Esempio minimale senza audio:

```python
import cv2


capture = cv2.VideoCapture("input.mp4")
fps = capture.get(cv2.CAP_PROP_FPS)
writer = None

while True:
    ok, frame = capture.read()
    if not ok:
        break

    upscaled = remote_upscaler.upscale_frame(
        frame,
        "RealESRGAN_x2plus",
    )

    if writer is None:
        height, width = upscaled.shape[:2]
        writer = cv2.VideoWriter(
            "output.mp4",
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (width, height),
        )

    writer.write(upscaled)

capture.release()
if writer is not None:
    writer.release()
```

Considerazioni pratiche:

- base64 aumenta la quantità di dati trasferiti rispetto ai bytes originali;
- un modello 4× moltiplica larghezza e altezza per quattro e il numero di pixel
  per sedici;
- il collo di bottiglia può diventare la rete, soprattutto frame per frame;
- non inviare molti frame in parallelo: il server li processa comunque in coda;
- per video lunghi può essere più efficiente caricare e processare direttamente
  l'intero video tramite l'interfaccia Colab;
- il client restituisce i frame nell'ordine delle chiamate sincrone.

## Checklist

Sul Colab:

- [ ] Runtime GPU abilitato
- [ ] Codice aggiornato con l'endpoint `upscale_image`
- [ ] `GRADIO_SHARE=true`
- [ ] Token configurato prima dell'avvio, se richiesto
- [ ] Cella di `main.py` ancora in esecuzione
- [ ] URL pubblico copiato dall'output corrente

Nell'altra applicazione:

- [ ] Installati `requests`, `Pillow` e `numpy`
- [ ] Copiato/importato `remote_upscale.py`
- [ ] Configurati URL e token senza inserirli nel repository
- [ ] Usato un nome modello valido
- [ ] Gestita `RemoteUpscaleError`
- [ ] Timeout adeguato al primo download del modello
- [ ] Chiamate frame mantenute in ordine e senza parallelismo inutile

## File di riferimento

- Server/API: [`tabs/upscaler_tab.py`](../tabs/upscaler_tab.py)
- Client riutilizzabile: [`utils/remote_upscale.py`](../utils/remote_upscale.py)
- Client CLI: [`remote_upscale_client.py`](../remote_upscale_client.py)
- Setup Colab: [`colab/COLAB_SETUP.md`](../colab/COLAB_SETUP.md)
- Test del contratto: [`tests/test_remote_upscale.py`](../tests/test_remote_upscale.py)
