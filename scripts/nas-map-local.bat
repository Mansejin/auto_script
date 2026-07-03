@echo off
setlocal
cd /d "%~dp0.." || (echo ERROR & pause & exit /b 1)

echo.
echo [NAS] Map docker share to a drive letter (Y: if Z: is busy)
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0nas-pc.ps1" map -Profile local
set "ERR=%ERRORLEVEL%"

if %ERR% neq 0 (
  echo.
  echo Tip: edit config\nas-pc.local.env - NAS_DRIVE_LETTER=Y
  pause
  exit /b %ERR%
)

echo.
pause
endlocal
