@echo off
setlocal
cd /d "%~dp0.." || (echo ERROR & pause & exit /b 1)

echo Copy SSH public key to Synology NAS...
echo Password asked ONE last time.
echo.

type "%USERPROFILE%\.ssh\id_ed25519.pub" | ssh saenggibu-nas-local "mkdir -p /var/services/homes/ohola/.ssh && cat >> /var/services/homes/ohola/.ssh/authorized_keys && chmod 700 /var/services/homes/ohola/.ssh && chmod 600 /var/services/homes/ohola/.ssh/authorized_keys"

if errorlevel 1 (
  echo.
  echo FAILED. Enable User Home in DSM first:
  echo   Control Panel - User - Advanced - Enable user home service
  echo.
  pause
  exit /b 1
)

echo.
echo OK. Test: ssh saenggibu-nas-local
echo Add to config\nas-pc.local.env :
echo   NAS_SSH_KEY=%USERPROFILE%\.ssh\id_ed25519
echo Then run: powershell -File scripts\nas-pc.ps1 setup
echo.
pause
endlocal
