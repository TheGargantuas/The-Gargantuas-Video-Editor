"""
Configuration file for the Video Editor application
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
TEMP_DIR = BASE_DIR / "temp"
CONFIG_DIR = BASE_DIR / "config"

# YouTube Configuration (for Support tab)
YOUTUBE_CHANNEL_URL = "https://www.youtube.com/@TheGargantuas"
YOUTUBE_CHANNEL_HANDLE = "@TheGargantuas"
YOUTUBE_PLAYLIST_ID = "PLBixPeNJ5K5YKII-nu9t7VAAFI6gO7ArL"
YOUTUBE_PLAYLIST_URL = f"https://www.youtube.com/playlist?list={YOUTUBE_PLAYLIST_ID}"
YOUTUBE_SUBSCRIBE_URL = f"{YOUTUBE_CHANNEL_URL}?sub_confirmation=1"

# RealESRGAN Models Configuration
MODELS = {
    "RealESRGAN_x4plus": {
        "scale": 4,
        "model_name": "RealESRGAN_x4plus",
        "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
        "description": "General purpose, best quality/performance balance",
        "default": True
    },
    "RealESRGAN_x2plus": {
        "scale": 2,
        "model_name": "RealESRGAN_x2plus",
        "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth",
        "description": "Lighter upscaling"
    },
    "RealESRNet_x4plus": {
        "scale": 4,
        "model_name": "RealESRNet_x4plus",
        "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.1/RealESRNet_x4plus.pth",
        "description": "Cleaner, less aggressive enhancement"
    },
    "RealESRGAN_x4plus_anime_6B": {
        "scale": 4,
        "model_name": "RealESRGAN_x4plus_anime_6B",
        "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth",
        "description": "Optimized for anime/cartoon content"
    }
}

# Device options
DEVICE_OPTIONS = ["CPU", "GPU (CUDA)", "MPS (Apple Silicon)"]

# Color scheme
COLOR_SCHEME = {
    "primary": "#FFA500",      # Amber
    "secondary": "#DC143C",    # Red
    "background": "#1A1A1A",   # Near black
    "surface": "#2D2D2D",      # Dark gray
    "text": "#FFFFFF",         # White
    "text_secondary": "#B0B0B0"  # Light gray
}

# Create necessary directories
def ensure_directories():
    """Create required directories if they don't exist"""
    TEMP_DIR.mkdir(exist_ok=True, parents=True)
    CONFIG_DIR.mkdir(exist_ok=True, parents=True)

# Session file
SESSION_FILE = CONFIG_DIR / "session.json"
