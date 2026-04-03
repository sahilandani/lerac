@echo off
echo Stopping Streamlit app...
taskkill /IM python.exe /F > nul 2>&1

echo Stopping Ollama server...
taskkill /IM ollama.exe /F > nul 2>&1

echo System stopped.