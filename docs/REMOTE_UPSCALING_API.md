# API REST per Upscaling remoto su Google Colab

Questa API permette a un'altra applicazione di usare la GPU di Google Colab per
fare upscaling di un'immagine oppure di un segmento video. Per i video non è
più necessario inviare un frame per richiesta: MLSM Studio crea segmenti da
un numero configurabile di frame (100 per default, fino a 5000) e li distribuisce in parallelo fra più runtime Colab.

Non c'è nessun token da creare o configurare. Per chiamare l'API serve soltanto
l'URL pubblico generato da Gradio, per esempio:

```text
https://abc123.gradio.live
```

## Endpoint disponibili

| Endpoint | Cosa fa | Input |
|---|---|---|
| `upscale_models` | Restituisce tutti i modelli disponibili | Nessuno |
| `upscale_image` | Esegue l'upscaling | Immagine base64 e nome modello |
| `upscale_video_chunk` | Upscala ed encode un segmento MP4 | MP4 base64, modello, frame attesi (1–5000), FPS (0 = originali) |

Il flusso da integrare è questo:

```text
1. Chiama upscale_models
2. Mostra i modelli nel tuo menu/dropdown
3. L'utente sceglie un modello
4. Chiama upscale_image con immagine + nome scelto
5. Per una foto chiama `upscale_image`; per un video distribuisci segmenti da
   il numero configurato di frame con `upscale_video_chunk`
6. Salva ogni segmento restituito prima di assegnare altro lavoro
```

## Avviare il server su Colab

1. In Colab seleziona **Runtime → Change runtime type → T4 GPU**.
2. Esegui il setup in [`colab/COLAB_SETUP.md`](../colab/COLAB_SETUP.md).
3. Avvia `main.py` con `GRADIO_SHARE=true`.
4. Copia l'indirizzo pubblico `https://...gradio.live` mostrato nell'output.
5. Lascia la cella in esecuzione.

Quando il runtime Colab viene chiuso, anche l'URL smette di funzionare. Al nuovo
avvio dovrai aggiornare l'URL nella tua applicazione.

## Come funzionano le chiamate REST Gradio

I due endpoint si chiamano in modo diverso:

- `upscale_models` è immediato e richiede una sola `POST`;
- `upscale_image` usa la coda Gradio perché l'elaborazione può durare: una
  `POST` crea il job e una `GET` recupera il risultato.

Le chiamate complete sono:

```text
POST {GRADIO_URL}/gradio_api/api/upscale_models

POST {GRADIO_URL}/gradio_api/call/upscale_image
GET  {GRADIO_URL}/gradio_api/call/upscale_image/{EVENT_ID}

POST {GRADIO_URL}/gradio_api/call/upscale_video_chunk
GET  {GRADIO_URL}/gradio_api/call/upscale_video_chunk/{EVENT_ID}
```

Il client Python incluso gestisce automaticamente anche i percorsi usati dalle
versioni precedenti di Gradio.

## 1. Recuperare l'elenco dei modelli

### POST

```http
POST https://abc123.gradio.live/gradio_api/api/upscale_models
Content-Type: application/json

{
  "data": []
}
```

Con `curl`:

```bash
curl -X POST \
  "https://abc123.gradio.live/gradio_api/api/upscale_models" \
  -H "Content-Type: application/json" \
  -d '{"data":[]}'
```

Non serve una seconda richiesta. La risposta Gradio contiene direttamente il
catalogo dentro `data[0]`:

```json
{
  "data": [
    {
      "ok": true,
      "default_model": "RealESRGAN_x4plus",
      "models": ["..."]
    }
  ],
  "is_generating": false
}
```

Nel tuo codice la risposta utile si legge quindi con
`response.json()["data"][0]`.

### Risposta completa dei modelli

```json
{
  "ok": true,
  "default_model": "RealESRGAN_x4plus",
  "models": [
    {
      "name": "RealESRGAN_x4plus",
      "scale": 4,
      "description": "General purpose, best quality/performance balance",
      "default": true
    },
    {
      "name": "RealESRGAN_x2plus",
      "scale": 2,
      "description": "Lighter upscaling",
      "default": false
    },
    {
      "name": "RealESRNet_x4plus",
      "scale": 4,
      "description": "Cleaner, less aggressive enhancement",
      "default": false
    },
    {
      "name": "RealESRGAN_x4plus_anime_6B",
      "scale": 4,
      "description": "Optimized for anime/cartoon content",
      "default": false
    }
  ]
}
```

Nella tua applicazione usa `models[].name` come valore del menu e
`models[].description` come testo visibile. Non mantenere una lista di modelli
hardcoded: richiamando questo endpoint la tua app vedrà automaticamente eventuali
modelli aggiunti in futuro.

## 2. Eseguire l'upscaling

L'immagine deve essere inviata come data URL base64:

```text
data:image/png;base64,iVBORw0KGgoAAA...
```

La lista `data` contiene esattamente due valori e l'ordine è importante:

```text
data[0] = immagine base64
data[1] = nome del modello
```

### POST

```http
POST https://abc123.gradio.live/gradio_api/call/upscale_image
Content-Type: application/json

{
  "data": [
    "data:image/png;base64,iVBORw0KGgoAAA...",
    "RealESRGAN_x4plus"
  ]
}
```

Risposta:

```json
{
  "event_id": "fedcba9876543210"
}
```

### GET del risultato

```http
GET https://abc123.gradio.live/gradio_api/call/upscale_image/fedcba9876543210
```

Alla fine dello stream riceverai:

```text
event: complete
data: [{"ok":true,"image":"data:image/png;base64,...","model":"RealESRGAN_x4plus","scale":4,"device":"GPU (CUDA)","info":"..."}]
```

La risposta utile, cioè il primo elemento della lista, ha questa struttura:

```json
{
  "ok": true,
  "image": "data:image/png;base64,iVBORw0KGgoAAA...",
  "model": "RealESRGAN_x4plus",
  "scale": 4,
  "device": "GPU (CUDA)",
  "info": "Image upscaled successfully..."
}
```

Il campo `image` contiene il risultato. Rimuovi la parte prima della virgola,
decodifica il resto da base64 e ottieni i bytes dell'immagine.

## 3. Upscaling di un segmento video

Il catalogo espone il contratto supportato:

```json
{"api_version":3,"capabilities":{"image_upscale":true,"video_chunks":true,"chunk_frames":100,"max_chunk_frames":5000,"preserve_source_fps":true,"optional_output_fps":true}}
```

`upscale_video_chunk` accetta quattro valori ordinati:

```text
data[0] = MP4 come data:video/mp4;base64,...
data[1] = nome modello
data[2] = numero esatto di frame, da 1 a max_chunk_frames
data[3] = FPS di uscita; 0 mantiene gli FPS del segmento
```

Il risultato contiene un MP4 H.264 senza audio e i metadati verificabili:

```json
{
  "ok": true,
  "api_version": 3,
  "video": "data:video/mp4;base64,...",
  "model": "RealESRGAN_x4plus",
  "scale": 4,
  "device": "GPU (CUDA)",
  "frame_count": 100,
  "fps": 30.0,
  "width": 3840,
  "height": 2160
}
```

Il server rifiuta segmenti oltre `max_chunk_frames` o con un conteggio diverso da
quello dichiarato. I file temporanei della richiesta vengono eliminati dopo
aver costruito la risposta. L'audio non attraversa Colab: resta nel file
originale e viene ripristinato una sola volta dal coordinatore locale dopo aver
verificato e ordinato tutti i segmenti.

Sia l'interfaccia standalone sia l'API mantengono per default tutti i frame e
il frame rate originale. Non esiste alcuna conversione automatica a 25 FPS:
la cadenza cambia soltanto quando l'utente passa esplicitamente un valore FPS.

## Codice REST pronto da copiare

Questo esempio non usa il client del progetto: esegue direttamente le chiamate
REST e può essere adattato alla tua applicazione.

```python
import base64
import json
from pathlib import Path

import requests


GRADIO_URL = "https://abc123.gradio.live"


def call_gradio(endpoint, data, timeout=900):
    endpoint_url = f"{GRADIO_URL}/gradio_api/call/{endpoint}"

    submission = requests.post(
        endpoint_url,
        json={"data": data},
        timeout=30,
    )
    submission.raise_for_status()
    event_id = submission.json()["event_id"]

    current_event = None
    event_data = []

    with requests.get(
        f"{endpoint_url}/{event_id}",
        stream=True,
        timeout=(10, timeout),
    ) as stream:
        stream.raise_for_status()

        for line in stream.iter_lines(decode_unicode=True):
            if line.startswith("event:"):
                current_event = line.removeprefix("event:").strip()
            elif line.startswith("data:"):
                event_data.append(line.removeprefix("data:").strip())
            elif line == "":
                if current_event == "error":
                    raise RuntimeError("Errore restituito da Gradio")

                if current_event == "complete":
                    outputs = json.loads("\n".join(event_data))
                    return outputs[0]

                current_event = None
                event_data = []

    raise RuntimeError("Stream terminato senza un risultato")


def get_models():
    request = requests.post(
        f"{GRADIO_URL}/gradio_api/api/upscale_models",
        json={"data": []},
        timeout=30,
    )
    request.raise_for_status()
    response = request.json()["data"][0]
    if not response["ok"]:
        raise RuntimeError(response["error"])
    return response


def upscale_file(input_path, output_path, model_name):
    input_path = Path(input_path)
    mime_type = "image/png" if input_path.suffix.lower() == ".png" else "image/jpeg"
    encoded = base64.b64encode(input_path.read_bytes()).decode("ascii")
    image_payload = f"data:{mime_type};base64,{encoded}"

    response = call_gradio(
        "upscale_image",
        [image_payload, model_name],
    )
    if not response["ok"]:
        raise RuntimeError(response["error"])

    encoded_output = response["image"].split(",", 1)[1]
    Path(output_path).write_bytes(base64.b64decode(encoded_output))
    return response


# 1. Recupera i modelli dal server
models_response = get_models()
for model in models_response["models"]:
    print(model["name"], model["scale"], model["description"])

# 2. Usa il modello selezionato dalla tua interfaccia
selected_model = models_response["default_model"]
result = upscale_file("frame.png", "frame_upscaled.png", selected_model)
print(result["device"], result["scale"])
```

## Uso con il client Python incluso

Se la tua applicazione è Python, il modo più semplice è copiare
[`utils/remote_upscale.py`](../utils/remote_upscale.py) nel tuo progetto.

Installa soltanto:

```bash
pip install requests Pillow numpy
```

Poi:

```python
from remote_upscale import RemoteUpscaleClient


client = RemoteUpscaleClient("https://abc123.gradio.live")

# Recupera i modelli senza conoscerne prima i nomi
catalog = client.list_models()
for model in catalog["models"]:
    print(model["name"], model["description"])

# Usa il modello scelto dalla tua UI
selected_model = catalog["default_model"]
client.upscale_to_file(
    "frame.png",
    selected_model,
    "frame_upscaled.png",
)
```

Per un frame OpenCV:

```python
import cv2


frame = cv2.imread("frame.png")
upscaled_frame = client.upscale_frame(frame, selected_model)
cv2.imwrite("frame_upscaled.png", upscaled_frame)
```

`upscale_frame()` riceve e restituisce frame OpenCV in formato BGR.

## Client da terminale

Per vedere i modelli esposti dal server:

```bash
python remote_upscale_client.py \
  --url https://abc123.gradio.live \
  --list-models
```

Per fare upscaling:

```bash
python remote_upscale_client.py \
  --url https://abc123.gradio.live \
  --input frame.png \
  --output frame_upscaled.png \
  --model RealESRGAN_x4plus
```

## Errori

Un errore applicativo viene restituito così:

```json
{
  "ok": false,
  "error": "Unsupported model: nome-errato",
  "available_models": [
    "RealESRGAN_x4plus",
    "RealESRGAN_x2plus",
    "RealESRNet_x4plus",
    "RealESRGAN_x4plus_anime_6B"
  ]
}
```

Controlla sempre `ok` prima di leggere `image` o `models`.

Altri errori comuni:

| Errore | Significato |
|---|---|
| Endpoint non trovato | Il Colab non usa ancora la versione aggiornata del progetto |
| Timeout/connessione rifiutata | Il runtime è spento oppure l'URL Gradio è cambiato |
| Input oltre 25 MB | Riduci l'immagine oppure modifica `UPSCALE_API_MAX_INPUT_MB` sul Colab |
| CUDA out of memory | Usa il modello 2× o un'immagine più piccola |

## File interessati

- Endpoint Gradio: [`tabs/upscaler_tab.py`](../tabs/upscaler_tab.py)
- Client Python: [`utils/remote_upscale.py`](../utils/remote_upscale.py)
- Client CLI: [`remote_upscale_client.py`](../remote_upscale_client.py)
- Test: [`tests/test_remote_upscale.py`](../tests/test_remote_upscale.py)
