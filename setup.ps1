# 디디딧 시트 도구 초기 설정 (Windows)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Python = "C:\Users\Ohola\AppData\Local\Python\bin\python.exe"
if (-not (Test-Path $Python)) {
    $Python = (Get-Command py -ErrorAction SilentlyContinue).Source
    if ($Python) { $Python = "py" }
    else { throw "Python을 찾을 수 없습니다. Python 3.10+ 설치 후 다시 실행하세요." }
}

if (-not (Test-Path ".env")) {
    Copy-Item "config.example.env" ".env"
    Write-Host "[OK] .env 생성됨"
}

& $Python -m venv .venv --clear
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt -q
Write-Host "[OK] 가상환경 및 패키지 설치 완료"
Write-Host ""
Write-Host "다음 단계:"
Write-Host "  1. credentials\oauth-client.json 에 OAuth 클라이언트 JSON 저장"
Write-Host "  2. .\.venv\Scripts\python.exe cli.py auth"
Write-Host "  3. .env 에서 WORKSHEET_NAME(시트 탭 이름) 확인"
Write-Host "  4. .\.venv\Scripts\python.exe cli.py list-parts"
