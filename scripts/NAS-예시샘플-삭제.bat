@echo off
setlocal
cd /d "%~dp0.." || (echo ERROR & pause & exit /b 1)
echo Remove example samples from T:\saenggibu\data\saenggibu\samples
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0nas-cleanup-example-samples.ps1" %*
endlocal
