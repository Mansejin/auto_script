@echo off
chcp 65001 >nul
cd /d "%~dp0.."
title Saenggibu local dev
echo.
echo Folder: %CD%
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dev-local.ps1" %*
if errorlevel 1 (
  echo.
  echo ========================================
  echo  Server failed to start
  echo ========================================
  echo.
  echo Common fixes:
  echo   1. Install Python 3.10+ from python.org
  echo   2. Turn OFF Windows "App execution aliases" for python.exe
  echo   3. Open NEW terminal after install
  echo   4. Run: py -3 --version
  echo.
  pause
)
