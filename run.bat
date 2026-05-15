@echo off
echo ===========================================
echo Starting PDF Search Engine...
echo ===========================================

cd /d "%~dp0"

IF NOT EXIST "pdfs" (
    mkdir pdfs
)

echo Checking for Python installation...
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check 'Add Python to PATH' during installation.
    pause
    exit /b
)

echo Setting up the engine...
IF NOT EXIST "venv" (
    echo Creating virtual environment... (This only happens the first time)
    python -m venv venv
)

echo Activating environment...
call venv\Scripts\activate

echo Installing required libraries (including OCR dependencies)...
pip install fastapi uvicorn pymupdf pytesseract pillow watchdog -q

echo.
echo ===========================================
echo Engine is ready! Starting the server...
echo ===========================================
echo Keep this window open. Do not close it.
echo Your app is running! Open your browser and go to:
echo.
echo    http://localhost:8000
echo.
echo ===========================================
echo.

cd backend
python -m uvicorn main:app --reload --port 8000
