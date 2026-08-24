# 🚀 Google Colab Setup Guide

## Quick Start (3 Steps)

### Method 1: Copy the Complete Setup Script (Recommended)

Copy the entire content from [colab_notebook_setup.py](colab_notebook_setup.py) into a Colab cell and run it.

This script:
- ✅ Installs Python 3.11 in virtual environment
- ✅ Installs cryptography BEFORE other dependencies
- ✅ Sets up PyTorch, Gradio, and all required packages
- ✅ Configures Matplotlib backend for Colab
- ✅ Enables public sharing automatically

### Method 2: Manual Setup (Step-by-Step)

Run these commands in separate Colab cells:

```bash
# Cell 1: Setup environment
%cd /content
!rm -rf The-Gargantuas-Video-Editor py311
!apt-get update -y && apt-get install -y ffmpeg git curl python3.11 python3.11-venv python3.11-distutils
!python3.11 -m venv /content/py311
!/content/py311/bin/python -m pip install --upgrade pip setuptools wheel

# Cell 2: Clone repository
!git clone https://github.com/TheGargantuas/The-Gargantuas-Video-Editor.git
%cd /content/The-Gargantuas-Video-Editor

# Cell 3: Install PyTorch
!/content/py311/bin/pip install --no-cache-dir numpy==1.26.4
!/content/py311/bin/pip install --no-cache-dir torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2

# Cell 4: Install cryptography FIRST (CRITICAL!)
!/content/py311/bin/pip install --no-cache-dir cryptography==46.0.5

# Cell 5: Install core dependencies
!/content/py311/bin/pip install --no-cache-dir gradio opencv-python==4.9.0.80 pillow ffmpeg-python python-dotenv

# Cell 6: Install AI models dependencies
!/content/py311/bin/pip install --no-cache-dir basicsr realesrgan gfpgan facexlib librosa soundfile scipy pydub

# Cell 7: Install subtitle tools
!/content/py311/bin/pip install --no-cache-dir faster-whisper openai

# Cell 8: Configure Matplotlib and launch
%env MPLBACKEND=Agg
%env GRADIO_SHARE=true
!/content/py311/bin/python main.py
```

---

## ⚠️ CRITICAL: Why Install Order Matters

**WRONG** (causes ModuleNotFoundError):
```bash
!/content/py311/bin/pip install gradio opencv-python pillow  # ❌ cryptography not installed yet
!/content/py311/bin/python main.py  # ❌ ERROR: No module named 'cryptography'
```

**CORRECT** (works every time):
```bash
!/content/py311/bin/pip install cryptography==46.0.5  # ✅ Install BEFORE launching app
!/content/py311/bin/pip install gradio opencv-python pillow
!/content/py311/bin/python main.py  # ✅ Works!
```

**Why?** 
- `main.py` imports `utils.api_key_manager` immediately at startup
- `api_key_manager.py` needs `cryptography.fernet` at import time  
- Must install `cryptography` BEFORE running `main.py`
- The [complete setup script](colab_notebook_setup.py) handles this automatically

---

## GPU Setup (Recommended)

1. **Enable GPU**: Runtime → Change runtime type → **T4 GPU**
2. Verify GPU:
   ```python
   import torch
   print(f"GPU Available: {torch.cuda.is_available()}")
   print(f"GPU Name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")
   ```

---

## API Keys Setup

### Option 1: Groq (RECOMMENDED - 100k tokens/day FREE)
1. Get API key: https://console.groq.com/keys
2. In app: Settings tab → Enter key → Save

### Option 2: OpenAI (Pay-as-you-go)
1. Get API key: https://platform.openai.com/api-keys
2. In app: Settings tab → Enter key → Save

### Option 3: Gemini (20 requests/day free)
1. Get API key: https://makersuite.google.com/app/apikey
2. In app: Settings tab → Enter key → Save

---

## Troubleshooting

### ❌ ModuleNotFoundError: No module named 'cryptography'

**Cause**: Installed dependencies in wrong order

**Fix**:
```bash
# Restart runtime (Runtime → Restart runtime)
# Then install cryptography FIRST:
!pip install cryptography==46.0.5
!pip install -r requirements.txt
```

### ❌ CUDA Out of Memory

**Cause**: GPU not enabled or model too large

**Fix**:
1. Enable GPU: Runtime → Change runtime type → GPU
2. Use smaller models:
   - Whisper: `medium` instead of `large-v3`
   - Lip Sync: `LivePortrait` (fastest)
3. Restart runtime if needed

### ❌ Daily Quota Exceeded (Gemini)

**Cause**: Exceeded Gemini's 20 requests/day limit

**Fix**:
1. Switch to Groq (100k tokens/day):
   - Get key: https://console.groq.com/keys
   - Settings tab → Change provider to Groq
2. Use **Single Pass** mode (1 call vs 12-16)

### 🐌 Slow Generation

**Causes**: CPU-only mode or large models

**Fixes**:
1. Enable GPU (see GPU Setup above)
2. Use faster models:
   - Whisper: `base` (fastest) or `medium` (balanced)
   - Lip Sync: `LivePortrait` (fastest)
3. Reduce quality settings if needed

---

## Performance Tips

### API Provider Comparison
| Provider | Free Tier | API Calls/Subtitle | Speed |
|----------|-----------|-------------------|-------|
| **Groq** (★ Best) | 100k tokens/day | Single: 1 call | ⚡⚡⚡ |
| Gemini | 20 req/day | Single: 1 call | ⚡⚡ |
| OpenAI | Pay-as-you-go | Single: 1 call | ⚡ |

### Validation Mode
- **Single Pass** (★ Recommended):
  - 1 API call total
  - Fast generation
  - Good quality
  - Perfect for Gemini free tier

- **Multi-Agent**:
  - 12-16 API calls
  - Best quality
  - Slower
  - Better with Groq (more quota)

### Recommended Settings
```yaml
Provider: Groq (free 100k tokens/day)
Validation: Single Pass
Whisper Model: large-v3 (best quality)
Subtitle Format: SRT
Max Characters per Line: 42
Max Lines per Subtitle: 2
```

---

## Colab-Specific Features

### Public URL Sharing
The app automatically enables public sharing on Colab:
```python
# Automatically set in Colab environment
os.environ['GRADIO_SHARE'] = 'true'
```

You'll get a public URL like: `https://xxxxx.gradio.live`

### Remote Upscaling API

The same public URL exposes the named `upscale_image` endpoint. A local program
can send an image or OpenCV frame and a RealESRGAN model name while inference
runs on the Colab GPU.

Because a Gradio share URL is public, you can protect the endpoint by setting a
token in a cell before launching the app:

```python
%env UPSCALE_API_TOKEN=replace-with-a-long-random-value
```

From the local repository, call it with:

```bash
python remote_upscale_client.py \
  --url https://xxxxx.gradio.live \
  --input frame.png \
  --output frame_upscaled.png \
  --model RealESRGAN_x4plus \
  --token replace-with-a-long-random-value
```

See [Remote Upscaling API](../docs/REMOTE_UPSCALING_API.md) for raw REST and
Python/OpenCV integration examples.

### Session Persistence
⚠️ **Warning**: Colab sessions are temporary!
- Download generated files before closing
- API keys are stored in memory only
- Re-enter keys after runtime restart

### Resource Limits
- **Free Tier**:
  - 12 hours max session
  - T4 GPU (when available)
  - ~12GB RAM
  
- **Colab Pro**:
  - 24 hours max session
  - Better GPUs (A100, V100)
  - ~25GB RAM

---

## Common Workflows

### 1. Generate Subtitles (Word-by-Word Karaoke)

```python
# Use Groq for free tier
1. Settings → Add Groq API key
2. Audio to Subtitles tab:
   - Upload audio + lyrics
   - Clean Lyrics
   - Transcribe (Whisper large-v3)
   - Select Provider: Groq
   - Mode: word_by_word (karaoke)
   - Validation: Single Pass
   - Generate Subtitles
3. Download SRT file
```

### 2. Lip Sync Video

```python
# Fastest method
1. Lip Sync tab:
   - Upload video + audio
   - Model: LivePortrait (fastest)
   - Click Generate
2. Wait ~5-10 minutes (depends on video length)
3. Download result
```

### 3. Upscale Video

```python
# Balance quality/speed
1. Upscaler tab:
   - Upload video
   - Scale: 2x (recommended)
   - Model: RealESRGAN
   - Click Upscale
2. Download result
```

---

## Need Help?

- **Bug Reports**: Open issue on GitHub
- **Feature Requests**: Open issue with `[Feature]` tag
- **Questions**: Check existing issues or documentation

---

## Resources

- **Main README**: [README.md](../README.md)
- **Project Structure**: [docs/PROJECT_STRUCTURE.md](../docs/PROJECT_STRUCTURE.md)
- **Groq Console**: https://console.groq.com
- **OpenAI Platform**: https://platform.openai.com
- **Gemini API**: https://makersuite.google.com

---

## License

See [LICENSE](../LICENSE) file for details.
