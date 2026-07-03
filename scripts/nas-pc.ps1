#Requires -Version 5.1
<#
.SYNOPSIS
  PC에서 나스 SSH·SMB를 쉽게 쓰기 위한 스크립트

.EXAMPLE
  .\scripts\nas-pc.ps1 setup      # 최초 1회: 설정 파일 + SSH config
  .\scripts\nas-pc.ps1 connect    # SSH 접속
  .\scripts\nas-pc.ps1 update     # 나스에서 pull + docker 재빌드
  .\scripts\nas-pc.ps1 map        # docker 폴더를 Z: 드라이브로 연결
  .\scripts\nas-pc.ps1 status     # 연결 상태 확인
#>
param(
  [Parameter(Position = 0)]
  [ValidateSet("setup", "connect", "update", "logs", "map", "unmap", "status")]
  [string]$Command = "connect"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ExampleConfig = Join-Path $Root "config\nas-pc.example.env"
$LocalConfig = Join-Path $Root "config\nas-pc.local.env"

function Write-Info([string]$Message) { Write-Host $Message -ForegroundColor Cyan }
function Write-Ok([string]$Message) { Write-Host $Message -ForegroundColor Green }
function Write-Warn([string]$Message) { Write-Host $Message -ForegroundColor Yellow }

function Read-EnvFile([string]$Path) {
  $result = @{}
  if (-not (Test-Path $Path)) { return $result }
  Get-Content $Path -Encoding UTF8 | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    $idx = $line.IndexOf("=")
    if ($idx -lt 1) { return }
    $key = $line.Substring(0, $idx).Trim()
    $value = $line.Substring($idx + 1).Trim()
    $result[$key] = $value
  }
  return $result
}

function Get-NasConfig {
  if (-not (Test-Path $LocalConfig)) {
    throw "설정 파일이 없습니다. 먼저 실행: .\scripts\nas-pc.ps1 setup"
  }
  $cfg = Read-EnvFile $LocalConfig
  $required = @("NAS_SSH_HOST", "NAS_USER", "NAS_REPO_PATH")
  foreach ($key in $required) {
    if (-not $cfg[$key]) { throw "config/nas-pc.local.env 에 $key 가 필요합니다." }
  }
  if (-not $cfg["NAS_SSH_ALIAS"]) { $cfg["NAS_SSH_ALIAS"] = "saenggibu-nas" }
  if (-not $cfg["NAS_SSH_PORT"]) { $cfg["NAS_SSH_PORT"] = "22" }
  if (-not $cfg["NAS_SMB_HOST"]) { $cfg["NAS_SMB_HOST"] = $cfg["NAS_SSH_HOST"] }
  if (-not $cfg["NAS_SMB_SHARE"]) { $cfg["NAS_SMB_SHARE"] = "docker" }
  if (-not $cfg["NAS_DRIVE_LETTER"]) { $cfg["NAS_DRIVE_LETTER"] = "Z" }
  return $cfg
}

function Ensure-OpenSsh {
  $ssh = Get-Command ssh -ErrorAction SilentlyContinue
  if (-not $ssh) {
    throw @"
OpenSSH 클라이언트가 없습니다.
Windows 설정 → 앱 → 선택적 기능 → 'OpenSSH 클라이언트' 설치 후 다시 실행하세요.
"@
  }
}

function Get-SshConfigPath {
  $dir = Join-Path $env:USERPROFILE ".ssh"
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
  return Join-Path $dir "config"
}

function Install-SshConfig([hashtable]$Cfg) {
  $alias = $Cfg["NAS_SSH_ALIAS"]
  $path = Get-SshConfigPath
  $block = @"

Host $alias
  HostName $($Cfg["NAS_SSH_HOST"])
  Port $($Cfg["NAS_SSH_PORT"])
  User $($Cfg["NAS_USER"])
"@

  if ($Cfg["NAS_SSH_KEY"]) {
    $key = $Cfg["NAS_SSH_KEY"] -replace '\\', '/'
    $block += "`n  IdentityFile $key"
  }

  $existing = ""
  if (Test-Path $path) { $existing = Get-Content $path -Raw -Encoding UTF8 }
  if ($existing -match "(?ms)^Host\s+$alias\s*$") {
    Write-Warn "SSH config에 이미 '$alias' 가 있습니다. 건너뜁니다."
    return
  }

  Add-Content -Path $path -Value $block -Encoding UTF8
  Write-Ok "SSH config 등록됨 → ssh $alias"
}

function Invoke-NasSetup {
  if (-not (Test-Path $LocalConfig)) {
    Copy-Item $ExampleConfig $LocalConfig
    Write-Ok "config/nas-pc.local.env 생성됨"
  }

  Write-Host ""
  Write-Info "메모장으로 설정 파일을 엽니다. NAS_SSH_HOST, NAS_USER 만 맞게 고치고 저장하세요."
  Write-Warn "Tailscale 쓰면 NAS_SSH_HOST=100.x.x.x (나스 Tailscale IP) 가 제일 편합니다."
  Start-Process notepad.exe $LocalConfig
  Read-Host "저장한 뒤 Enter"

  $cfg = Get-NasConfig
  Ensure-OpenSsh
  Install-SshConfig $cfg

  Write-Host ""
  Write-Ok "설정 완료"
  Write-Host "  SSH 접속:     .\scripts\nas-pc.ps1 connect"
  Write-Host "  나스 업데이트: .\scripts\nas-pc.ps1 update"
  Write-Host "  SMB 연결:     .\scripts\nas-pc.ps1 map   (DSM 공유폴더 설정 후)"
}

function Invoke-NasConnect {
  $cfg = Get-NasConfig
  Ensure-OpenSsh
  Install-SshConfig $cfg
  Write-Info "접속 중: ssh $($cfg['NAS_SSH_ALIAS'])"
  ssh $cfg["NAS_SSH_ALIAS"]
}

function Invoke-NasRemote([string]$RemoteCommand) {
  $cfg = Get-NasConfig
  Ensure-OpenSsh
  Install-SshConfig $cfg
  ssh $cfg["NAS_SSH_ALIAS"] $RemoteCommand
}

function Invoke-NasUpdate {
  $cfg = Get-NasConfig
  $repo = $cfg["NAS_REPO_PATH"]
  Write-Info "나스 업데이트 실행 중…"
  Invoke-NasRemote "cd '$repo' && sh scripts/nas-docker-update.sh"
  Write-Ok "완료"
}

function Invoke-NasLogs {
  $cfg = Get-NasConfig
  $repo = $cfg["NAS_REPO_PATH"]
  Invoke-NasRemote "cd '$repo' && docker compose logs -f --tail=80"
}

function Invoke-NasMap {
  $cfg = Get-NasConfig
  $letter = $cfg["NAS_DRIVE_LETTER"].TrimEnd(":")
  $unc = "\\$($cfg['NAS_SMB_HOST'])\$($cfg['NAS_SMB_SHARE'])"

  $existing = net use "${letter}:" 2>$null
  if ($LASTEXITCODE -eq 0) {
    Write-Warn "${letter}: 드라이브가 이미 연결되어 있습니다. 해제 후 다시 시도: .\scripts\nas-pc.ps1 unmap"
    return
  }

  Write-Info "SMB 연결: $unc → ${letter}:"
  Write-Warn "DSM에서 'docker' 공유 폴더 + SMB 가 켜져 있어야 합니다. (docs/nas-pc-access.md)"
  cmd /c "net use ${letter}: `"$unc`" /persistent:yes"
  if ($LASTEXITCODE -ne 0) {
    throw "SMB 연결 실패. DSM 공유 폴더·계정·Tailscale(밖에서 접속 시) 확인"
  }
  Write-Ok "${letter}: → $unc 연결됨 (탐색기에서 docker 폴더 사용 가능)"
}

function Invoke-NasUnmap {
  $cfg = Get-NasConfig
  $letter = $cfg["NAS_DRIVE_LETTER"].TrimEnd(":")
  cmd /c "net use ${letter}: /delete /y"
  Write-Ok "${letter}: 연결 해제"
}

function Invoke-NasStatus {
  $cfg = Get-NasConfig
  Write-Host "SSH alias : $($cfg['NAS_SSH_ALIAS'])"
  Write-Host "SSH host  : $($cfg['NAS_SSH_HOST']):$($cfg['NAS_SSH_PORT'])"
  Write-Host "SMB       : \\$($cfg['NAS_SMB_HOST'])\$($cfg['NAS_SMB_SHARE']) → $($cfg['NAS_DRIVE_LETTER']):"
  Write-Host "Repo      : $($cfg['NAS_REPO_PATH'])"
  Write-Host ""

  Ensure-OpenSsh
  Write-Info "SSH 핑…"
  ssh -o BatchMode=yes -o ConnectTimeout=8 $cfg["NAS_SSH_ALIAS"] "echo ok" 2>$null
  if ($LASTEXITCODE -eq 0) { Write-Ok "SSH 연결 OK" } else { Write-Warn "SSH 연결 실패 (setup·Tailscale·DSM SSH 확인)" }

  $letter = $cfg["NAS_DRIVE_LETTER"].TrimEnd(":")
  if (Test-Path "${letter}:\") { Write-Ok "SMB ${letter}: 연결됨" } else { Write-Warn "SMB ${letter}: 미연결 (.\scripts\nas-pc.ps1 map)" }
}

Set-Location $Root

switch ($Command) {
  "setup" { Invoke-NasSetup }
  "connect" { Invoke-NasConnect }
  "update" { Invoke-NasUpdate }
  "logs" { Invoke-NasLogs }
  "map" { Invoke-NasMap }
  "unmap" { Invoke-NasUnmap }
  "status" { Invoke-NasStatus }
}
