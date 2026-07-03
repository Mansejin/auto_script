@echo off
setlocal
cd /d "%~dp0.." || (echo ERROR: cannot find project folder & pause & exit /b 1)

echo.
echo [NAS] Tailscale SSH
echo Project: %CD%
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0nas-pc.ps1" connect -Profile remote
set "ERR=%ERRORLEVEL%"

if %ERR% neq 0 (
  echo.
  echo [FAILED] exit code %ERR%
  echo Check Tailscale is running on PC and NAS.
  echo.
  pause
  exit /b %ERR%
)

endlocal
