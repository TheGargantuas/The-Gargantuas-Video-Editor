# 📚 Video Editor - Documentation

Benvenuto nella documentazione completa di **Video Editor**!

## 📖 Guide Disponibili

### 🚀 [Quick Start](QUICKSTART.md)
Guida rapida per installare e avviare l'applicazione in pochi minuti.

**Contenuti:**
- Installazione rapida
- Primo avvio
- Test dell'applicazione

---

### 👄 [LipSync Guide](LIPSYNC.md)
Guida completa all'utilizzo del tab LipSync per sincronizzare labbra con audio.

**Contenuti:**
- 6 modelli AI disponibili (Wav2Lip, Wav2Lip GAN, SadTalker, Video-Retalking, LivePortrait, The Gargantuas Hybrid)
- Come usare il LipSync per immagini e video
- Impostazioni avanzate e ottimizzazioni
- Risoluzione problemi comuni
- Tempi di processing e requisiti hardware

---

### 🔧 [OpenCV Patch](OPENCV_PATCH.md)
Documentazione tecnica sulla patch di compatibilità OpenCV.

**Contenuti:**
- Problema di compatibilità tra opencv-python e opencv-python-headless
- Soluzione implementata (auto-applicata all'avvio)
- Costanti OpenCV patchate
- Troubleshooting

---

### 🌐 [Remote Upscaling API](REMOTE_UPSCALING_API.md)
Guida completa per integrare l'upscaling su GPU Colab in un'altra applicazione.

**Contenuti:**
- Avvio e protezione dell'endpoint pubblico Gradio
- Client Python riutilizzabile per file, PIL e frame OpenCV
- Contratto REST/SSE e struttura delle risposte
- Modelli, configurazione, errori e prestazioni video

---

### 🏗️ [Project Structure](PROJECT_STRUCTURE.md)
Organizzazione del codice e struttura del progetto.

**Contenuti:**
- Albero delle directory
- Descrizione di ogni componente
- File principali e loro funzioni

---

### 📝 [Changelog](CHANGELOG.md)
Storia delle versioni e aggiornamenti del progetto.

**Contenuti:**
- Versioni rilasciate
- Nuove funzionalità
- Bug fix
- Breaking changes

---

## 🔗 Link Rapidi

| Risorsa | Link |
|---------|------|
| **README Principale** | [../README.md](../README.md) |
| **Installazione Setup** | [QUICKSTART.md](QUICKSTART.md) |
| **Guida LipSync** | [LIPSYNC.md](LIPSYNC.md) |
| **Remote Upscaling API** | [REMOTE_UPSCALING_API.md](REMOTE_UPSCALING_API.md) |
| **Struttura Progetto** | [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) |

## 🆘 Hai Bisogno di Aiuto?

1. **Problemi di installazione?** → Consulta [QUICKSTART.md](QUICKSTART.md)
2. **Errori LipSync?** → Vedi [LIPSYNC.md](LIPSYNC.md) sezione "Risoluzione Problemi"
3. **Errori OpenCV?** → Leggi [OPENCV_PATCH.md](OPENCV_PATCH.md)
4. **File non trovati?** → Controlla [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)
5. **Integrazione Colab da un'altra app?** → Consulta [REMOTE_UPSCALING_API.md](REMOTE_UPSCALING_API.md)

## 📌 Note

- Tutta la documentazione è in formato Markdown
- I link sono relativi al repository
- Documentazione aggiornata a Febbraio 2026

---

**← Torna al [README Principale](../README.md)**
