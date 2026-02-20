# Quick Start Guide

## Prerequisites
- macOS, Windows, or Linux
- Python 3.11+ installed (or pyenv)
- Internet connection for model downloads

## Installation

### Option 1: Using the Setup Script (Recommended)

#### macOS/Linux:
```bash
cd "Video Editor"
./setup.sh
```

#### Windows:
```cmd
cd "Video Editor"
setup.bat
```

### Option 2: Manual Installation

1. **Set Python version** (if using pyenv):
```bash
pyenv install 3.11.0
pyenv local 3.11.0
```

2. **Create virtual environment**:
```bash
python -m venv venv
```

3. **Activate virtual environment**:

macOS/Linux:
```bash
source venv/bin/activate
```

Windows:
```cmd
venv\Scripts\activate.bat
```

4. **Install dependencies**:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Running the Application

1. **Activate virtual environment** (if not already active):

macOS/Linux:
```bash
source .venv/bin/activate
```

Windows:
```cmd
.venv\Scripts\activate.bat
```

2. **Start the application**:
```bash
python main.py
```

3. **Open in browser**:
   - The application will start at `http://localhost:7860`
   - Your browser should open automatically
   - If not, manually navigate to the URL shown in the terminal

## First Run

### Authentication Steps

1. **Start Authentication**:
   - Click "🔐 Start Google Authentication"
   - Your browser will open with Google's login page

2. **Authorize the App**:
   - Log in to your Google account
   - Grant the requested permissions
   - You'll be redirected to a page that may show an error (this is normal)

3. **Get the Authorization Code**:
   - Look at the URL in your browser
   Using the Application

No authentication or setup required! Just start using the features.

### Upscaler Tab
4. **Choose Output Format**:
   - PNG: Lossless, larger files
   - JPG: Smaller files, slight quality loss
   - WebP: Modern format, good compression

5. **Upscale**:
   - Click "🚀 Upscale Image"
   - Wait for processing (few seconds to minutes)
   - Download result from "Upscaled Image" panel

**Video Upscaling**

1. **Select Model & Device** (same as image)

2. **Upload Video**:
   - Click "Input Video" area
   - Select video file
   - **Note**: Processing is very slow, start with short clips

3. **Set FPS** (optional):
   - Leave empty to keep original FPS
   - Or set custom frame rate

4. **Upscale**:
   - Click "🚀 Upscale Video"
   - **Be patient**: This takes a long time
   - Progress bar will show current status
   - Download result when complete

### Support Tab

If you find the app useful, check out the **Support Me** tab to:
- Subscribe to the creator's YouTube channel
- Watch featured content
- Learn about other ways to support the project

## Common Issues

### Slow processing

### Image Upscaling
- Use PNG output for maximum quality
- RealESRGAN_x4plus works well for most photos
- Try RealESRNet_x4plus if results look too "enhanced"
- Anime model (anime_6B) is specifically trained for drawn content

### Video Upscaling
- Start with very short clips (10-30 seconds) to test
- Use GPU/MPS acceleration (CPU is extremely slow)
- Consider processing longer videos in segments
- Original FPS is usually best
- Expect 10-30 minutes per minute of footage

Not applicable - no authentication required!

### Slow processingied the entire code
- Try the authentication process again
- Check that client_secrets.json is present

### "Subscription not found"
- Make sure you're logged into the correct Google account
- Subscribe to the channel and wait a minute
- Try verifying again

### "Out of memory"
- Close other applications
- Use 2x model instead of 4x
- Fo"Out of memory"
- Close other applications
- Use 2x model instead of 4x
- For videos, process shorter segments

### r videos, process shorter segments

### Slow processing
- Make sure GPU/MPS is selected (not CPU)
- First run needs to download models
- Video processing is inherently slow

### Models not downloading
- Check internet connection
- Firewall may be blocking download
- Try running again

## Getting Help

1. Check `NOTES.md` for detailed information
2. Read `SETUP_GOOGLE_AUTH.md` for authentication help
3. Review error messages in the terminal
4. Chview error messages in the terminal
3. Check available VRAM/RAM if getting crashes

## Next Steps

- Experiment with different models
- Try upscaling various content types
- Check out the **Support Me** tab if you enjoy the app!
- Stay tuned for new features!

---

**Made with ❤️ - 100% Free Forever!**