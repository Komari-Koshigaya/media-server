@echo off
title Media Server
cd /d "%~dp0"
python -m media_server --port 18080
pause
