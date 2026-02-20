# Video Editor - AI-Powered Upscaler

A Python-based video editing application with AI upscaling capabilities.

## Features

- **AI Upscaling**: Upscale images and videos using RealESRGAN models
- **100% Free**: No login, no subscriptions, no locked features
- **Multi-device Support**: CPU, GPU (CUDA), and MPS (Apple Silicon) acceleration
- **Cross-platform**: Compatible with macOS, Windows, and Linux
- **Easy to Use**: Simple interface with powerful features
- **Open Source**: Free software you can trust

## Setup

### Quick Setup (Recommended)

#### macOS/Linux:
```bash
chmod +x setup.sh
./setup.sh
```

#### Windows:
```cmd
setup.bat
```

The setup script will automatically:
- Check/install Python 3.11.0 (via pyenv)
- Create virtual environment (`.venv`)
- Install all dependencies

### Manual Installation

If you prefer to install manually:

1. **Install Python 3.11.0**:
```bash
pyenv install 3.11.0
pyenv local 3.11.0
```

2. **Create and activate virtual environment**:
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# OR
.venv\Scripts\activate.bat  # Windows
```

3. **Install dependencies**:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Running the Application

### Quick Start (Easiest Method)

For users who have already run the setup script, you can start the app with a single command:

#### macOS/Linux:
```bash
./run.sh
```

#### Windows:
```cmd
run.bat
```

These scripts automatically:
- Activate the virtual environment
- Start the application
- No need to remember Python commands!

### Manual Start

If you prefer to run manually:

1. **Activate virtual environment** (if not already active):
```bash
source .venv/bin/activate  # macOS/Linux
# OR
.venv\Scripts\activate.bat  # Windows
```

2. **Run the app**:
```bash
python main.py
```

The app will open in your browser at `http://localhost:7860`

## Usage

1. Launch the application:
   - **macOS/Linux**: `./run.sh`
   - **Windows**: `run.bat`
2. Use the **Upscaler** tab to process images and videos
3. Open the **🔍 Video Comparison Modal** to see examples of different models
4. Check out the **❤️ Support Me** tab if you find the app useful!

The app is completely free and works without any login or registration!

## Supported Upscaling Models

| Model | Description | Base Video | Example Video |
|-------|-------------|------------|---------------|
| **RealESRGAN_x4plus** (default) | 4x scale, general purpose | [▶️ Base](example/example_video/base.mp4) | [▶️ Upscaled](example/example_video/example%20RealESRGAN_x4plus.mp4) |
| **RealESRGAN_x2plus** | 2x scale, lighter upscaling | [▶️ Base](example/example_video/base.mp4) | [▶️ Upscaled](example/example_video/example%20RealESRGAN_x2plus.mp4) |
| **RealESRNet_x4plus** | 4x scale, cleaner output | [▶️ Base](example/example_video/base.mp4) | [▶️ Upscaled](example/example_video/example%20RealESRNet_x4plus.mp4) |
| **RealESRGAN_x4plus_anime_6B** | 4x scale, optimized for anime/cartoon content | [▶️ Base](example/example_video/base.mp4) | [▶️ Upscaled](example/example_video/example%20RealESRGAN_x4plus_anime_6B.mp4) |

> 💡 **Tip**: Download the repository to view the example videos locally and compare the quality differences between models.

## Features in Detail

### AI Upscaling
- Automatic detection of image vs video files
- Audio preservation for videos (automatically extracted and re-added)
- Progress tracking with performance metrics (seconds/frame, ETA)
- Multiple AI models optimized for different content types

### Performance Monitoring
- Real-time progress updates in Gradio interface
- Terminal output with timing information per frame
- Final statistics: total time, average s/frame, processing speed

### Video Comparison Modal
- Side-by-side comparison of original vs upscaled videos
- Example videos for all models included
- Synchronized playback controls
- Loop functionality for continuous comparison
- Native aspect ratio preservation

## Dependencies & Credits

This project is built with amazing open source technologies:

### Core Technologies
- **[Gradio](https://gradio.app/)** (Apache 2.0) - Web interface framework
- **[PyTorch](https://pytorch.org/)** (BSD-style) - Deep learning framework
- **[RealESRGAN](https://github.com/xinntao/Real-ESRGAN)** (BSD 3-Clause) - AI upscaling models
- **[BasicSR](https://github.com/XPixelGroup/BasicSR)** (Apache 2.0) - Super-resolution framework

### Additional Libraries
- **OpenCV** - Image/video processing
- **FFmpeg** - Video encoding/decoding
- **Pillow** - Image manipulation
- **NumPy** - Numerical computing

Special thanks to all contributors and maintainers of these projects!

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

