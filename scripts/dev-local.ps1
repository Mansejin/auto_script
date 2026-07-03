param(
  [int]$Port = 8787,
  [switch]$NoBrowser,
  [switch]$Reload
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Write-Step([string]$Text) {
  Write-Host ">> $Text" -ForegroundColor Cyan
}

function Test-PythonExe([string]$Exe, [string[]]$Prefix = @()) {
  if (-not $Exe) { return $false }
  if ($Exe -like "*\Microsoft\WindowsApps\*") { return $false }
  try {
    & $Exe @Prefix -c "import sys" 2>$null | Out-Null
    return $LASTEXITCODE -eq 0
  } catch {
    return $false
  }
}

function Invoke-ProjectPython {
  param([string[]]$PythonArgs)
  & $script:PythonExe @script:PythonPrefix @PythonArgs
  if ($LASTEXITCODE -ne 0) {
    throw "Python failed (exit $LASTEXITCODE): $($script:PythonPrefix -join ' ') $($PythonArgs -join ' ')"
  }
}

function Test-ProjectImports {
  $code = @"
import dotenv, fastapi, uvicorn, multipart, itsdangerous, openpyxl, docx
"@
  try {
    Invoke-ProjectPython -PythonArgs @("-c", $code) | Out-Null
    return $true
  } catch {
    return $false
  }
}

Write-Host ""
Write-Host "========================================"
Write-Host " Saenggibu local dev server"
Write-Host "========================================"
Write-Host "Folder: $Root"
Write-Host ""

if (-not (Test-Path .env)) {
  Write-Step "Creating .env from config.example.env"
  Copy-Item config.example.env .env
  Write-Host "  Edit .env -> set ADMIN_PASSWORD and GEMINI_API_KEY"
}

$script:PythonExe = $null
$script:PythonPrefix = @()

$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pyLauncher -and (Test-PythonExe $pyLauncher.Source @("-3"))) {
  $script:PythonExe = $pyLauncher.Source
  $script:PythonPrefix = @("-3")
  Write-Step "Python: py -3"
}

if (-not $script:PythonExe) {
  foreach ($name in @("python", "python3")) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($cmd -and (Test-PythonExe $cmd.Source)) {
      $script:PythonExe = $cmd.Source
      $script:PythonPrefix = @()
      Write-Step "Python: $name ($($cmd.Source))"
      break
    }
  }
}

if (-not $script:PythonExe) {
  throw @"

Python not found (or only Windows Store stub).

Fix:
  1) Install Python 3.10+ from https://www.python.org/downloads/
  2) Check "Add python.exe to PATH"
  3) Windows Settings -> Apps -> App execution aliases
     -> turn OFF "python.exe" and "python3.exe" store aliases
  4) Open a NEW terminal and run again
"@
}

Write-Step "Installing / updating packages (requirements.txt)..."
Invoke-ProjectPython -PythonArgs @("-m", "pip", "install", "--upgrade", "pip")
Invoke-ProjectPython -PythonArgs @("-m", "pip", "install", "-r", "requirements.txt")

if (-not (Test-ProjectImports)) {
  throw "Package install incomplete. Run manually: python -m pip install -r requirements.txt"
}

$portInUse = $null
try {
  $portInUse = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
} catch {}
if ($portInUse) {
  throw "Port $Port is already in use. Close the other app or run: .\scripts\dev-local.ps1 -Port 8788"
}

$env:SGB_HOST = "127.0.0.1"
$env:SGB_PORT = "$Port"
# Windows reload subprocess often breaks; UI edits only need browser refresh anyway.
$env:SGB_RELOAD = if ($Reload) { "1" } else { "0" }
$env:SGB_PLAN = "admin"
$env:SGB_ALLOWED_ORIGINS = "http://127.0.0.1:$Port,http://localhost:$Port"

$adminUrl = "http://127.0.0.1:$Port/admin/saenggibu"
$healthUrl = "http://127.0.0.1:$Port/health"

Write-Host ""
Write-Host "Server URLs"
Write-Host "  Admin : $adminUrl"
Write-Host "  Health: $healthUrl"
Write-Host "  Reload: $($env:SGB_RELOAD) (API code change -> restart this window)"
Write-Host ""
Write-Host "Keep this window OPEN while testing. Closing it stops the server." -ForegroundColor Green
Write-Host ""

if (-not $NoBrowser) {
  Start-Job -ScriptBlock {
    param($Url)
    Start-Sleep -Seconds 2
    Start-Process $Url
  } -ArgumentList $adminUrl | Out-Null
}

Invoke-ProjectPython -PythonArgs @("server.py")
