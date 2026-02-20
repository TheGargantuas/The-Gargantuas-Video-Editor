#!/bin/bash

# AI Video Upscaler - Quick Launcher
# This script activates the virtual environment and starts the application

echo "🚀 Starting AI Video Upscaler..."
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run setup.sh first to install dependencies."
    exit 1
fi

# Activate virtual environment
echo "✓ Activating virtual environment..."
source .venv/bin/activate

# Check if main.py exists
if [ ! -f "main.py" ]; then
    echo "❌ main.py not found!"
    exit 1
fi

# Start the application
echo "✓ Starting application..."
echo ""
python main.py
