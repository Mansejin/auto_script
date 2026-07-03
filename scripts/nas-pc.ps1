#Requires -Version 5.1
<#
.SYNOPSIS
  PC에서 나스 SSH·SMB를 쉽게 쓰기 위한 스크립트

.EXAMPLE
  .\scripts\nas-pc.ps1 setup
  .\scripts\nas-pc.ps1 connect              # Tailscale (외부)
  .\scripts\nas-pc.ps1 connect -Profile local   # 로컬 IP (집)
  .\scripts\nas-pc.ps1 update -Profile local
#>
param(
  [Parameter(Position = 0)]
  [ValidateSet("setup", "connect", "update", "logs", "map", "unmap", "status")]
  [string]$Command = "connect",

  [ValidateSet("remote", "local")]
  [string]$Profile = "remote"
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
  $required = @("NAS_USER", "NAS_REPO_PATH")
  foreach ($key in $required) {
    if (-not $cfg[$key]) { throw "config/nas-pc.local.env 에 $key 가 필요합니다." }
  }
  if (-not $cfg["NAS_SSH_HOST"]) { $cfg["NAS_SSH_HOST"] = "ohola.synology.me" }
  if (-not $cfg["NAS_SSH_ALIAS"]) { $cfg["NAS_SSH_ALIAS"] = "saenggibu-nas" }
  if (-not $cfg["NAS_SSH_HOST_LOCAL"]) { $cfg["NAS_SSH_HOST_LOCAL"] = "169.254.158.191" }
  if (-not $cfg["NAS_SSH_ALIAS_LOCAL"]) { $cfg["NAS_SSH_ALIAS_LOCAL"] = "saenggibu-nas-local" }
  if (-not $cfg["NAS_SSH_PORT"]) { $cfg["NAS_SSH_PORT"] = "22" }
  if (-not $cfg["NAS_SMB_HOST"]) { $cfg["NAS_SMB_HOST"] = $cfg["NAS_SSH_HOST"] }
  if (-not $cfg["NAS_SMB_HOST_LOCAL"]) { $cfg["NAS_SMB_HOST_LOCAL"] = $cfg["NAS_SSH_HOST_LOCAL"] }
  if (-not $cfg["NAS_SMB_SHARE"]) { $cfg["NAS_SMB_SHARE"] = "docker" }
  if (-not $cfg["NAS_DRIVE_LETTER"]) { $cfg["NAS_DRIVE_LETTER"] = "Z" }
  return $cfg
}

function Resolve-NasProfile([hashtable]$Cfg, [string]$ProfileName) {
  if ($ProfileName -eq "local") {
    return @{
      Name    = "local"
      Label   = "로컬"
      Host    = $Cfg["NAS_SSH_HOST_LOCAL"]
      Alias   = $Cfg["NAS_SSH_ALIAS_LOCAL"]
      SmbHost = $Cfg["NAS_SMB_HOST_LOCAL"]
    }
  }
  return @{
    Name    = "remote"
    Label   = "Tailscale"
    Host    = $Cfg["NAS_SSH_HOST"]
    Alias   = $Cfg["NAS_SSH_ALIAS"]
    SmbHost = $Cfg["NAS_SMB_HOST"]
  }
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

function Install-SshHost([hashtable]$Cfg, [string]$Alias, [string]$HostName) {
  $path = Get-SshConfigPath
  $block = @"

Host $Alias
  HostName $HostName
  Port $($Cfg["NAS_SSH_PORT"])
  User $($Cfg["NAS_USER"])
"@

  if ($Cfg["NAS_SSH_KEY"]) {
    $key = $Cfg["NAS_SSH_KEY"] -replace '\\', '/'
    $block += "`n  IdentityFile $key"
  }

  $existing = ""
  if (Test-Path $path) { $existing = Get-Content $path -Raw -Encoding UTF8 }
  if ($existing -match "(?ms)^Host\s+$([regex]::Escape($Alias))\s*$") {
    return $false
  }

  Add-Content -Path $path -Value $block -Encoding UTF8
  return $true
}

function Install-AllSshConfigs([hashtable]$Cfg) {
  $remote = Resolve-NasProfile $Cfg "remote"
  $local = Resolve-NasProfile $Cfg "local"

  if (Install-SshHost $Cfg $remote.Alias $remote.Host) {
    Write-Ok "SSH 등록: $($remote.Alias) → $($remote.Host) (외부/Tailscale)"
  }
  if (Install-SshHost $Cfg $local.Alias $local.Host) {
    Write-Ok "SSH 등록: $($local.Alias) → $($local.Host) (로컬)"
  }
}

function Invoke-NasSetup {
  if (-not (Test-Path $LocalConfig)) {
    Copy-Item $ExampleConfig $LocalConfig
    Write-Ok "config/nas-pc.local.env 생성됨"
  }

  Write-Host ""
  Write-Info "설정 파일을 엽니다. NAS_USER, Tailscale IP, 로컬 IP 를 맞추고 저장하세요."
  Write-Warn "로컬 IP 기본값: 169.254.158.191 (NAS_SSH_HOST_LOCAL)"
  Start-Process notepad.exe $LocalConfig
  Read-Host "저장한 뒤 Enter"

  $cfg = Get-NasConfig
  Ensure-OpenSsh
  Install-AllSshConfigs $cfg

  Write-Host ""
  Write-Ok "설정 완료"
  Write-Host "  집(로컬):  scripts\NAS-접속-로컬.bat"
  Write-Host "  밖(TS):    scripts\NAS-접속.bat"
  Write-Host "  업데이트:  scripts\NAS-업데이트-로컬.bat / NAS-업데이트.bat"
}

function Invoke-NasConnect {
  $cfg = Get-NasConfig
  $profile = Resolve-NasProfile $cfg $Profile
  Ensure-OpenSsh
  Install-AllSshConfigs $cfg
  Write-Info "접속 중 [$($profile.Label)]: ssh $($profile.Alias) ($($profile.Host))"
  ssh $profile.Alias
}

function Invoke-NasRemote([string]$RemoteCommand) {
  $cfg = Get-NasConfig
  $profile = Resolve-NasProfile $cfg $Profile
  Ensure-OpenSsh
  Install-AllSshConfigs $cfg
  ssh $profile.Alias $RemoteCommand
}

function Invoke-NasUpdate {
  $cfg = Get-NasConfig
  $repo = $cfg["NAS_REPO_PATH"]
  $profile = Resolve-NasProfile $cfg $Profile
  Write-Info "나스 업데이트 [$($profile.Label)]…"
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
  $profile = Resolve-NasProfile $cfg $Profile
  $letter = $cfg["NAS_DRIVE_LETTER"].TrimEnd(":")
  $unc = "\\$($profile.SmbHost)\$($cfg['NAS_SMB_SHARE'])"

  $existing = net use "${letter}:" 2>$null
  if ($LASTEXITCODE -eq 0) {
    Write-Warn "${letter}: 드라이브가 이미 연결되어 있습니다. 해제: .\scripts\nas-pc.ps1 unmap"
    return
  }

  Write-Info "SMB [$($profile.Label)]: $unc → ${letter}:"
  cmd /c "net use ${letter}: `"$unc`" /persistent:yes"
  if ($LASTEXITCODE -ne 0) {
    throw "SMB 연결 실패. DSM 공유 폴더·계정 확인"
  }
  Write-Ok "${letter}: → $unc 연결됨"
}

function Invoke-NasUnmap {
  $cfg = Get-NasConfig
  $letter = $cfg["NAS_DRIVE_LETTER"].TrimEnd(":")
  cmd /c "net use ${letter}: /delete /y"
  Write-Ok "${letter}: 연결 해제"
}

function Test-SshProfile([hashtable]$Cfg, [string]$ProfileName) {
  $profile = Resolve-NasProfile $Cfg $ProfileName
  ssh -o BatchMode=yes -o ConnectTimeout=6 $profile.Alias "echo ok" 2>$null
  return ($LASTEXITCODE -eq 0)
}

function Invoke-NasStatus {
  $cfg = Get-NasConfig
  $remote = Resolve-NasProfile $cfg "remote"
  $local = Resolve-NasProfile $cfg "local"

  Write-Host "=== Tailscale (외부) ==="
  Write-Host "  ssh $($remote.Alias)  →  $($remote.Host)"
  Write-Host "  smb \\$($remote.SmbHost)\$($cfg['NAS_SMB_SHARE'])"
  Write-Host ""
  Write-Host "=== 로컬 (집) ==="
  Write-Host "  ssh $($local.Alias)  →  $($local.Host)"
  Write-Host "  smb \\$($local.SmbHost)\$($cfg['NAS_SMB_SHARE'])"
  Write-Host ""
  Write-Host "Repo: $($cfg['NAS_REPO_PATH'])"
  Write-Host ""

  Ensure-OpenSsh
  Install-AllSshConfigs $cfg | Out-Null

  Write-Info "연결 테스트…"
  if (Test-SshProfile $cfg "local") { Write-Ok "로컬 SSH OK" } else { Write-Warn "로컬 SSH 실패" }
  if (Test-SshProfile $cfg "remote") { Write-Ok "Tailscale SSH OK" } else { Write-Warn "Tailscale SSH 실패 (밖에서만 되는 경우 정상)" }

  $letter = $cfg["NAS_DRIVE_LETTER"].TrimEnd(":")
  if (Test-Path "${letter}:\") { Write-Ok "SMB ${letter}: 연결됨" } else { Write-Warn "SMB ${letter}: 미연결" }
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
