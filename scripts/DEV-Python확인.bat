@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo Checking Python...
where py >nul 2>&1 && (py -3 --version && goto :ok)
where python >nul 2>&1 && (python --version && goto :ok)
echo.
echo [FAIL] Python not found.
echo Install from https://www.python.org/downloads/
echo Then disable Store aliases: Settings - Apps - App execution aliases
pause
exit /b 1
:ok
echo.
echo OK. Run scripts\DEV-로컬테스트.bat to start the server.
pause
