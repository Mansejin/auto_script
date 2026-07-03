@echo off
setlocal
cd /d "%~dp0.." || (echo ERROR & pause & exit /b 1)

set "SRC=%CD%\web\admin"
set "DEST=T:\saenggibu\web\admin"

if not exist "T:\" (
  echo T: drive not mapped. Run: net use T: \\169.254.158.191\docker
  pause
  exit /b 1
)

if not exist "%DEST%" (
  echo DEST not found: %DEST%
  echo Try: T:\saenggibu\web\admin or check T: path
  pause
  exit /b 1
)

echo Copy admin UI to NAS...
echo   from %SRC%
echo   to   %DEST%
xcopy /E /Y /I "%SRC%\*" "%DEST%\"
echo.
echo Done. Refresh browser (Ctrl+F5).
echo If delete still fails, run NAS update once for API:
echo   .\scripts\nas-pc.ps1 update -Profile local
pause
endlocal
