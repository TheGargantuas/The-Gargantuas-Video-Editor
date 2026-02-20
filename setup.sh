#!/bin/bash

# Setup script for Video Editor application

echo "================================================"
echo "Video Editor - Setup Script"
echo "================================================"
echo ""

# Check if pyenv is installed
if ! command -v pyenv &> /dev/null; then
    echo "❌ pyenv is not installed. Please install it first:"
    echo "   macOS: brew install pyenv"
    echo "   Or visit: https://github.com/pyenv/pyenv#installation"
    exit 1
fi

echo "✓ pyenv found"

# Check Python version
PYTHON_VERSION="3.11.0"
if pyenv versions | grep -q "$PYTHON_VERSION"; then
    echo "✓ Python $PYTHON_VERSION already installed"
else
    echo "📦 Installing Python $PYTHON_VERSION..."
    pyenv install $PYTHON_VERSION
fi

# Set local Python version
pyenv local $PYTHON_VERSION
echo "✓ Python version set to $PYTHON_VERSION"

# Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
echo ""
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
echo "   This may take several minutes..."
pip install -r requirements.txt

echo ""
echo "================================================"
echo "✓ Setup Complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Run the application:"
echo "   source .venv/bin/activate"
echo "   python main.py"
echo ""
echo "The app will open in your browser at http://localhost:7860"
echo ""
