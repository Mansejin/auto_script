@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo API 재빌드 포함 업데이트 (사무실 로컬)
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\nas-pc.ps1" update-api -Profile local
pause
