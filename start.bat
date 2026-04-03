@echo off
where ollama >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: ollama not found in PATH.
    echo Please install Ollama and reboot terminal: https://ollama.com/
    pause
    exit /b 1
)

echo Starting Ollama server...
start "Ollama" /B ollama serve

echo Waiting for Ollama to start...
timeout /t 5 /nobreak > nul

echo Starting Streamlit app...
start "Streamlit" /B python -m streamlit run app.py

echo System started. Access the app at http://localhost:8501