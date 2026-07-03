@echo off
setlocal
cd /d "%~dp0.."
echo Remove example samples from T:\saenggibu\data\saenggibu\samples
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\nas-cleanup-example-samples.ps1" %*
pause
endlocal
