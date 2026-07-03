@echo off
setlocal
cd /d "%~dp0.." || (echo ERROR: cannot find project folder & pause & exit /b 1)

echo.
echo [NAS] Local SSH - 169.254.158.191
echo Project: %CD%
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0nas-pc.ps1" connect -Profile local
set "ERR=%ERRORLEVEL%"

if %ERR% neq 0 (
  echo.
  echo [FAILED] exit code %ERR%
  echo.
  echo Check:
  echo   1. config\nas-pc.local.env exists and NAS_USER is set
  echo   2. DSM - Control Panel - Terminal - SSH enabled
  echo   3. NAS IP is correct (DSM network settings)
  echo   4. Run once: powershell -File scripts\nas-pc.ps1 setup
  echo.
  pause
  exit /b %ERR%
)

endlocal
