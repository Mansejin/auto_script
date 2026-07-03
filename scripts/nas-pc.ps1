#Requires -Version 5.1
<#
.SYNOPSIS
  NAS SSH/SMB helper for Windows (ASCII-only for PowerShell 5.1)

.EXAMPLE
  .\scripts\nas-pc.ps1 setup
  .\scripts\nas-pc.ps1 connect -Profile local
  .\scripts\nas-pc.ps1 connect -Profile remote
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
    throw "Missing config. Run: .\scripts\nas-pc.ps1 setup"
  }
  $cfg = Read-EnvFile $LocalConfig
  $required = @("NAS_USER", "NAS_REPO_PATH")
  foreach ($key in $required) {
    if (-not $cfg[$key]) { throw "Set $key in config/nas-pc.local.env" }
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
      Label   = "local"
      Host    = $Cfg["NAS_SSH_HOST_LOCAL"]
      Alias   = $Cfg["NAS_SSH_ALIAS_LOCAL"]
      SmbHost = $Cfg["NAS_SMB_HOST_LOCAL"]
    }
  }
  return @{
    Name    = "remote"
    Label   = "tailscale"
    Host    = $Cfg["NAS_SSH_HOST"]
    Alias   = $Cfg["NAS_SSH_ALIAS"]
    SmbHost = $Cfg["NAS_SMB_HOST"]
  }
}

function Ensure-OpenSsh {
  $ssh = Get-Command ssh -ErrorAction SilentlyContinue
  if (-not $ssh) {
    throw "OpenSSH client not found. Install via Windows Optional Features."
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
    Write-Ok "SSH: $($remote.Alias) -> $($remote.Host) (tailscale)"
  }
  if (Install-SshHost $Cfg $local.Alias $local.Host) {
    Write-Ok "SSH: $($local.Alias) -> $($local.Host) (local LAN)"
  }
}

function Invoke-NasSetup {
  if (-not (Test-Path $LocalConfig)) {
    Copy-Item $ExampleConfig $LocalConfig
    Write-Ok "Created config/nas-pc.local.env"
  }

  Write-Host ""
  Write-Info "Edit NAS_USER, NAS_SSH_HOST (tailscale), NAS_SSH_HOST_LOCAL (169.254.158.191)"
  Start-Process notepad.exe $LocalConfig
  Read-Host "Press Enter after saving"

  $cfg = Get-NasConfig
  Ensure-OpenSsh
  Install-AllSshConfigs $cfg

  Write-Host ""
  Write-Ok "Done."
  Write-Host "  Local SSH:     scripts\nas-connect-local.bat"
  Write-Host "  Remote SSH:    scripts\nas-connect-remote.bat"
  Write-Host "  Local update:  scripts\nas-update-local.bat"
}

function Invoke-NasConnect {
  $cfg = Get-NasConfig
  $profile = Resolve-NasProfile $cfg $Profile
  Ensure-OpenSsh
  Install-AllSshConfigs $cfg
  Write-Info "Connecting [$($profile.Label)]: ssh $($profile.Alias) ($($profile.Host))"
  ssh -o ConnectTimeout=10 $profile.Alias
  if ($LASTEXITCODE -ne 0) {
    throw "SSH failed (code $LASTEXITCODE). Check DSM SSH, IP $($profile.Host), password/key."
  }
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
  Write-Info "NAS update [$($profile.Label)]..."
  Invoke-NasRemote "cd '$repo' && sh scripts/nas-docker-update.sh"
  Write-Ok "Done"
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

  $null = net use "${letter}:" 2>$null
  if ($LASTEXITCODE -eq 0) {
    Write-Warn "Drive ${letter}: already mapped. Run: .\scripts\nas-pc.ps1 unmap"
    return
  }

  Write-Info "SMB [$($profile.Label)]: $unc -> ${letter}:"
  cmd /c "net use ${letter}: `"$unc`" /persistent:yes"
  if ($LASTEXITCODE -ne 0) {
    throw "SMB failed. Check DSM shared folder and credentials."
  }
  Write-Ok "Mapped ${letter}: to $unc"
}

function Invoke-NasUnmap {
  $cfg = Get-NasConfig
  $letter = $cfg["NAS_DRIVE_LETTER"].TrimEnd(":")
  cmd /c "net use ${letter}: /delete /y"
  Write-Ok "Unmapped ${letter}:"
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

  Write-Host "=== Tailscale (remote) ==="
  Write-Host "  ssh $($remote.Alias)  ->  $($remote.Host)"
  Write-Host "  smb \\$($remote.SmbHost)\$($cfg['NAS_SMB_SHARE'])"
  Write-Host ""
  Write-Host "=== Local LAN ==="
  Write-Host "  ssh $($local.Alias)  ->  $($local.Host)"
  Write-Host "  smb \\$($local.SmbHost)\$($cfg['NAS_SMB_SHARE'])"
  Write-Host ""
  Write-Host "Repo: $($cfg['NAS_REPO_PATH'])"
  Write-Host ""

  Ensure-OpenSsh
  Install-AllSshConfigs $cfg | Out-Null

  Write-Info "Testing SSH..."
  if (Test-SshProfile $cfg "local") { Write-Ok "Local SSH OK" } else { Write-Warn "Local SSH failed" }
  if (Test-SshProfile $cfg "remote") { Write-Ok "Tailscale SSH OK" } else { Write-Warn "Tailscale SSH failed (OK if not on tailnet)" }

  $letter = $cfg["NAS_DRIVE_LETTER"].TrimEnd(":")
  if (Test-Path "${letter}:\") { Write-Ok "SMB ${letter}: mapped" } else { Write-Warn "SMB ${letter}: not mapped" }
}

Set-Location $Root

try {
  switch ($Command) {
    "setup" { Invoke-NasSetup }
    "connect" { Invoke-NasConnect }
    "update" { Invoke-NasUpdate }
    "logs" { Invoke-NasLogs }
    "map" { Invoke-NasMap }
    "unmap" { Invoke-NasUnmap }
    "status" { Invoke-NasStatus }
  }
} catch {
  Write-Host ""
  Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
  exit 1
}
