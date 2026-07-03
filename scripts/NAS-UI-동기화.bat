@echo off
setlocal
cd /d "%~dp0.." || (echo ERROR & pause & exit /b 1)

powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\nas-pc.ps1" sync-ui -Profile local
pause
endlocal
