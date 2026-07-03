param(
  [int]$Port = 8787
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path .env)) {
  Copy-Item config.example.env .env
  Write-Host "Created .env from config.example.env — set ADMIN_PASSWORD and GEMINI_API_KEY"
}

$env:SGB_HOST = "127.0.0.1"
$env:SGB_PORT = "$Port"
$env:SGB_RELOAD = "1"
$env:SGB_PLAN = "admin"
if (-not $env:SGB_ALLOWED_ORIGINS) {
  $env:SGB_ALLOWED_ORIGINS = "http://127.0.0.1:$Port,http://localhost:$Port"
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $python) { throw "Python not found. Install Python 3.10+." }

if (-not (& $python.Source -c "import fastapi" 2>$null)) {
  Write-Host "Installing dependencies..."
  & $python.Source -m pip install -q -r requirements.txt
}

Write-Host ""
Write-Host "생기부 로컬 테스트 서버"
Write-Host "  Admin UI: http://127.0.0.1:$Port/admin/saenggibu"
Write-Host "  Health:   http://127.0.0.1:$Port/health"
Write-Host ""
Write-Host "· UI(web/admin) 수정 -> 저장 후 브라우저 새로고침"
Write-Host "· Python API 수정 -> 자동 재시작 (SGB_RELOAD=1)"
Write-Host "· NAS 배포는 기능 확인 후 하루 1~2회만"
Write-Host ""

& $python.Source server.py
