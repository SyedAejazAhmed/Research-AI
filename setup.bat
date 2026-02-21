@echo off
echo ====================================================
echo    Yukti Research AI - Setup (Windows)
echo ====================================================
echo.

echo [1/3] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH.
    pause
    exit /b
)

echo [2/3] Installing/Updating dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Warning: Some dependencies failed to install.
    echo Please check your internet connection or try "pip install -r requirements.txt" manually.
)

echo [3/3] Checking for Ollama...
curl http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo Note: Ollama is not detected at http://localhost:11434
    echo Please install Ollama from https://ollama.com and run "ollama pull llama3.2" to use the AI capabilities.
) else (
    echo ✅ Ollama detected!
)

echo.
echo ====================================================
echo Setup Complete!
echo You can now start the system by running: python run.py
echo ====================================================
echo.
pause
