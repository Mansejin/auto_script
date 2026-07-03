@echo off
setlocal
cd /d "%~dp0.." || (echo ERROR: cannot find project folder & pause & exit /b 1)

echo.
echo [NAS] Install SSH key (password asked ONE last time)
echo Project: %CD%
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0nas-pc.ps1" install-key -Profile local
set "ERR=%ERRORLEVEL%"

if %ERR% neq 0 (
  echo.
  echo [FAILED] exit code %ERR%
  pause
  exit /b %ERR%
)

echo.
echo Next: ssh saenggibu-nas-local  (no password)
echo.
pause
endlocal
