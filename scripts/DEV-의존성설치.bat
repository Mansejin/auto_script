@echo off
chcp 65001 >nul
cd /d "%~dp0.."
title Install Python packages
echo.
echo Folder: %CD%
echo.

set PY=
where py >nul 2>&1 && set PY=py -3
if not defined PY where python >nul 2>&1 && set PY=python
if not defined PY (
  echo [FAIL] Python not found.
  pause
  exit /b 1
)

echo Using: %PY%
%PY% -m pip install --upgrade pip
%PY% -m pip install -r requirements.txt
%PY% -c "import dotenv, fastapi, uvicorn; print('OK: all core packages installed')"
if errorlevel 1 (
  echo.
  echo [FAIL] install incomplete
  pause
  exit /b 1
)
echo.
echo Done. Now run scripts\DEV-로컬테스트.bat
pause
