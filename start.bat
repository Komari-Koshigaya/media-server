@echo off
title Media Server
cd /d "%~dp0"

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":18080" ^| findstr "LISTENING"') do (
    echo [Media Server] Killing old process on port 18080, PID: %%a
    taskkill /F /PID %%a >nul 2>&1
    timeout /t 1 /nobreak >nul
)

echo [Media Server] Starting...
python -m media_server --port 18080
pause