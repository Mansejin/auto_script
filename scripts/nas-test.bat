@echo off
setlocal
cd /d "%~dp0.." || (echo ERROR: cannot find project folder & pause & exit /b 1)

echo.
echo [NAS] Connection test
echo Project: %CD%
echo.

if not exist "config\nas-pc.local.env" (
  echo ERROR: config\nas-pc.local.env not found.
  echo Run: powershell -File scripts\nas-pc.ps1 setup
  echo.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0nas-pc.ps1" status
echo.
pause
endlocal
