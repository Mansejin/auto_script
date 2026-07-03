@echo off
setlocal
echo Fixing SSH config permissions for %USERNAME%...
echo.

set "SSH_DIR=%USERPROFILE%\.ssh"
set "SSH_CFG=%SSH_DIR%\config"

if not exist "%SSH_DIR%" (
  mkdir "%SSH_DIR%"
)

if exist "%SSH_CFG%" (
  icacls "%SSH_CFG%" /reset >nul 2>&1
  icacls "%SSH_CFG%" /inheritance:r >nul 2>&1
  icacls "%SSH_CFG%" /remove "Authenticated Users" >nul 2>&1
  icacls "%SSH_CFG%" /remove "Users" >nul 2>&1
  icacls "%SSH_CFG%" /remove "Everyone" >nul 2>&1
  icacls "%SSH_CFG%" /remove "UNKNOWN\UNKNOWN" >nul 2>&1
  icacls "%SSH_CFG%" /grant:r "%USERNAME%:F" >nul
  echo OK: %SSH_CFG%
) else (
  echo No config file yet - will be created on setup.
)

icacls "%SSH_DIR%" /inheritance:r >nul 2>&1
icacls "%SSH_DIR%" /grant:r "%USERNAME%:(OI)(CI)F" >nul

echo.
echo Done. Try again:
echo   ssh saenggibu-nas-local
echo.
pause
endlocal
