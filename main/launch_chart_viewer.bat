@echo off
REM Candlestick Chart Viewer Launcher
REM This script activates the virtual environment and launches the chart viewer

echo 🚀 Starting Candlestick Chart Viewer...
echo.

REM Check if virtual environment exists
if not exist "..\\.venv\\Scripts\\Activate.ps1" (
    echo ❌ Virtual environment not found!
    echo Please run from the HA-momentum-trading directory and ensure .venv exists
    pause
    exit /b 1
)

REM Activate virtual environment and run chart viewer
powershell -ExecutionPolicy Bypass -Command "& { ..\.venv\Scripts\Activate.ps1; python chart_viewer.py }"

pause