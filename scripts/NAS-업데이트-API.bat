@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo API 재빌드 포함 업데이트 (Python 변경 반영)
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\nas-pc.ps1" update-api
pause
