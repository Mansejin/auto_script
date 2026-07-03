param(
  [int]$Port = 8787,
  [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Write-Step([string]$Text) {
  Write-Host ">> $Text" -ForegroundColor Cyan
}

function Invoke-ProjectPython {
  param([string[]]$PythonArgs)
  if ($script:PythonLauncher -eq "py") {
    & py -3 @PythonArgs
  } else {
    & $script:PythonExe @PythonArgs
  }
  if ($LASTEXITCODE -ne 0) {
    throw "Python command failed (exit $LASTEXITCODE): $($PythonArgs -join ' ')"
  }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
Write-Host " 생기부 로컬 테스트 서버" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "폴더: $Root"
Write-Host ""

if (-not (Test-Path .env)) {
  Write-Step ".env 없음 -> config.example.env 복사"
  Copy-Item config.example.env .env
  Write-Host "  .env 를 열어 ADMIN_PASSWORD, GEMINI_API_KEY 를 설정하세요." -ForegroundColor DarkYellow
}

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
$pyCmd = Get-Command py -ErrorAction SilentlyContinue
$python3Cmd = Get-Command python3 -ErrorAction SilentlyContinue

if ($pythonCmd) {
  $script:PythonExe = $pythonCmd.Source
  $script:PythonLauncher = "python"
} elseif ($pyCmd) {
  $script:PythonExe = $pyCmd.Source
  $script:PythonLauncher = "py"
} elseif ($python3Cmd) {
  $script:PythonExe = $python3Cmd.Source
  $script:PythonLauncher = "python3"
} else {
  throw @"
Python 을 찾을 수 없습니다.
  1) https://www.python.org/downloads/ 에서 Python 3.10+ 설치
  2) 설치 시 'Add python.exe to PATH' 체크
  3) 터미널을 새로 연 뒤 다시 실행
"@
}

Write-Step "Python: $($script:PythonLauncher)"

try {
  Invoke-ProjectPython -PythonArgs @("-c", "import fastapi, uvicorn")
} catch {
  Write-Step "패키지 설치 중 (최초 1회)..."
  Invoke-ProjectPython -PythonArgs @("-m", "pip", "install", "-r", "requirements.txt")
}

$portInUse = $null
try {
  $portInUse = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
} catch {
  # Some Windows editions lack Get-NetTCPConnection; skip port check.
}
if ($portInUse) {
  throw "포트 $Port 이(가) 이미 사용 중입니다. 다른 프로그램을 끄거나 -Port 8788 로 다시 실행하세요."
}

$env:SGB_HOST = "127.0.0.1"
$env:SGB_PORT = "$Port"
$env:SGB_RELOAD = "1"
$env:SGB_PLAN = "admin"
$env:SGB_ALLOWED_ORIGINS = "http://127.0.0.1:$Port,http://localhost:$Port"

$adminUrl = "http://127.0.0.1:$Port/admin/saenggibu"
$healthUrl = "http://127.0.0.1:$Port/health"

Write-Host ""
Write-Host "서버 주소"
Write-Host "  Admin : $adminUrl"
Write-Host "  Health: $healthUrl"
Write-Host ""
Write-Host "이 창을 닫으면 서버가 종료됩니다. 테스트 중에는 창을 유지하세요." -ForegroundColor Green
Write-Host ""

if (-not $NoBrowser) {
  Start-Job -ScriptBlock {
    param($Url)
    Start-Sleep -Seconds 2
    Start-Process $Url
  } -ArgumentList $adminUrl | Out-Null
}

Invoke-ProjectPython -PythonArgs @("server.py")
