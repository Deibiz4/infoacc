@echo off
echo Iniciando servidor local de Antigravity...
start "" "http://localhost:8000"
python -m http.server 8000
pause
