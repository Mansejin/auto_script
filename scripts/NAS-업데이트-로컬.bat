@echo off
chcp 65001 >nul
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\nas-pc.ps1" update -Profile local
pause
