@echo off
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\nas-pc.ps1" deploy -Profile local
pause
