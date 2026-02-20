@echo off
REM AI Video Upscaler - Quick Launcher
REM This script activates the virtual environment and starts the application

echo.
echo Starting AI Video Upscaler...
echo.

REM Change to script directory
cd /d "%~dp0"

REM Check if virtual environment exists
if not exist ".venv\" (
    echo Virtual environment not found!
    echo Please run setup.bat first to install dependencies.
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Check if main.py exists
if not exist "main.py" (
    echo main.py not found!
    pause
    exit /b 1
)

REM Start the application
echo Starting application...
echo.
python main.py

pause
