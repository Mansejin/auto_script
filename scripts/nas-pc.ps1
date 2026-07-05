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
  [ValidateSet("setup", "connect", "update", "deploy", "logs", "map", "unmap", "status", "fix-ssh", "install-key", "sync-ui", "sync-data")]
  [string]$Command = "connect",

  [ValidateSet("remote", "local")]
  [Alias("Profile")]
  [string]$NasProfile = "remote",

  [string]$DriveLetter = ""
)

$script:NasProfile = $NasProfile

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

function Remove-SshHostBlock([string]$Alias) {
  $path = Get-SshConfigPath
  if (-not (Test-Path $path)) { return }
  $content = Get-Content $path -Raw -Encoding UTF8
  if (-not $content) { return }
  $pattern = "(?ms)^Host\s+$([regex]::Escape($Alias))\s*\r?\n(?:  .+\r?\n)*"
  $content = [regex]::Replace($content, $pattern, "").TrimEnd()
  if ($content) {
    Set-Content -Path $path -Value ($content + "`n") -Encoding UTF8 -NoNewline
  } else {
    Remove-Item $path -Force
  }
}

function Rewrite-AllSshConfigs([hashtable]$Cfg) {
  $remote = Resolve-NasProfile $Cfg "remote"
  $local = Resolve-NasProfile $Cfg "local"
  Remove-SshHostBlock $remote.Alias
  Remove-SshHostBlock $local.Alias
  Install-SshHost $Cfg $remote.Alias $remote.Host | Out-Null
  Install-SshHost $Cfg $local.Alias $local.Host | Out-Null
  Write-Ok "SSH config updated (with key if set)"
}

function Set-EnvValue([string]$Key, [string]$Value) {
  $lines = @()
  if (Test-Path $LocalConfig) {
    $lines = @(Get-Content $LocalConfig -Encoding UTF8)
  }
  $found = $false
  $out = foreach ($line in $lines) {
    if ($line -match "^$([regex]::Escape($Key))=") {
      $found = $true
      "$Key=$Value"
    } else {
      $line
    }
  }
  if (-not $found) { $out += "$Key=$Value" }
  Set-Content -Path $LocalConfig -Value $out -Encoding UTF8
}

function Fix-SshKeyPerms([string]$KeyPath) {
  if (-not (Test-Path $KeyPath)) { return }
  icacls $KeyPath /inheritance:r | Out-Null
  icacls $KeyPath /grant:r "${env:USERNAME}:R" | Out-Null
  $pub = "$KeyPath.pub"
  if (Test-Path $pub) {
    icacls $pub /inheritance:r | Out-Null
    icacls $pub /grant:r "${env:USERNAME}:R" | Out-Null
  }
}

function Invoke-InstallKey {
  $cfg = Get-NasConfig
  Ensure-OpenSsh
  Invoke-FixSshPerms

  $keyPath = $cfg["NAS_SSH_KEY"]
  if (-not $keyPath) {
    $keyPath = Join-Path (Join-Path $env:USERPROFILE ".ssh") "id_ed25519"
  }

  if (-not (Test-Path $keyPath)) {
    Write-Info "Creating SSH key: $keyPath"
    $dir = Split-Path $keyPath
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
    & ssh-keygen @("-t", "ed25519", "-f", $keyPath, "-N", "", "-C", "saenggibu-nas")
    if ($LASTEXITCODE -ne 0) {
      throw "ssh-keygen failed. Try manually: ssh-keygen -t ed25519 -f `"$keyPath`""
    }
  }

  if (-not (Test-Path "$keyPath.pub")) {
    throw "Public key missing: $keyPath.pub (ssh-keygen may have failed)"
  }

  Fix-SshKeyPerms $keyPath
  Set-EnvValue "NAS_SSH_KEY" $keyPath
  $cfg["NAS_SSH_KEY"] = $keyPath

  $profile = Resolve-NasProfile $cfg $script:NasProfile
  Install-SshHost $cfg $profile.Alias $profile.Host | Out-Null

  Write-Info "Copy public key to NAS [$($profile.Label)]..."
  Write-Warn "Enter NAS password ONE LAST TIME:"
  $user = $cfg["NAS_USER"]
  $homeDir = "/var/services/homes/$user"
  $remoteCmd = "if [ ! -d '$homeDir' ]; then echo SYNO_HOME_MISSING; exit 2; fi; umask 077; mkdir -p '$homeDir/.ssh'; cat >> '$homeDir/.ssh/authorized_keys'; chmod 700 '$homeDir/.ssh'; chmod 600 '$homeDir/.ssh/authorized_keys'"
  Get-Content "$keyPath.pub" -Raw | ssh $profile.Alias $remoteCmd

  if ($LASTEXITCODE -eq 2) {
    throw @"
Synology user home folder missing: /var/services/homes/$user
DSM: Control Panel - User and Group - Advanced - Enable user home service - Apply
Then log in to DSM once as $user and retry install-key.
"@
  }

  if ($LASTEXITCODE -ne 0) {
    throw "Failed to copy key to NAS."
  }

  Rewrite-AllSshConfigs $cfg
  Invoke-FixSshPerms

  Write-Info "Testing passwordless SSH..."
  if (Test-SshProfile $cfg $script:NasProfile) {
    Write-Ok "Key login OK for $($profile.Label)"
  } else {
    Write-Warn "Key test failed. On DSM: Control Panel - Terminal - enable SSH key auth if available."
  }
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
  Rewrite-AllSshConfigs $Cfg
}

function Build-SshArgs([hashtable]$Cfg) {
  $sshOpts = @("-o", "ConnectTimeout=15", "-p", $Cfg["NAS_SSH_PORT"])
  if ($Cfg["NAS_SSH_KEY"]) {
    $sshOpts += @("-i", $Cfg["NAS_SSH_KEY"])
  }
  return $sshOpts
}

function Invoke-NasSsh([hashtable]$Cfg, [hashtable]$Target, [string]$RemoteCommand) {
  $hostAddr = "$($Cfg['NAS_USER'])@$($Target.Host)"
  $sshOpts = Build-SshArgs $Cfg
  Write-Info "SSH [$($Target.Label)]: $hostAddr"
  if ($RemoteCommand) {
    & ssh @sshOpts $hostAddr $RemoteCommand
  } else {
    & ssh @sshOpts $hostAddr
  }
  if ($LASTEXITCODE -ne 0) {
    throw "SSH failed (code $LASTEXITCODE) to $($Target.Host)"
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
  Rewrite-AllSshConfigs $cfg

  Write-Host ""
  Write-Ok "Done."
  Write-Host "  Local SSH:     scripts\nas-connect-local.bat"
  Write-Host "  Remote SSH:    scripts\nas-connect-remote.bat"
  Write-Host "  Local update:  scripts\nas-update-local.bat"
}

function Invoke-NasConnect {
  $cfg = Get-NasConfig
  $profile = Resolve-NasProfile $cfg $script:NasProfile
  Ensure-OpenSsh
  Rewrite-AllSshConfigs $cfg | Out-Null
  Invoke-NasSsh $cfg $profile ""
}

function Invoke-NasRemote([string]$RemoteCommand) {
  $cfg = Get-NasConfig
  $profile = Resolve-NasProfile $cfg $script:NasProfile
  Ensure-OpenSsh
  Invoke-NasSsh $cfg $profile $RemoteCommand
}

function Write-NasUnixFile([string]$Src, [string]$Dest) {
  $text = [System.IO.File]::ReadAllText($Src)
  $text = $text -replace "`r`n", "`n" -replace "`r", "`n"
  $utf8NoBom = New-Object System.Text.UTF8Encoding $false
  [System.IO.File]::WriteAllText($Dest, $text, $utf8NoBom)
}

function Find-NasMappedRepo([hashtable]$Cfg) {
  $checked = @{}
  $letters = @($Cfg["NAS_DRIVE_LETTER"].TrimEnd(":").ToUpper())
  $letters += @("K", "T", "Y", "Z", "X", "W", "V", "U", "S", "R")
  foreach ($letter in $letters) {
    if (-not $letter -or $letter.Length -ne 1) { continue }
    if ($checked.ContainsKey($letter)) { continue }
    $checked[$letter] = $true
    $repo = "${letter}:\saenggibu"
    if (Test-Path $repo) { return $repo }
  }
  foreach ($drive in Get-PSDrive -PSProvider FileSystem) {
    if ($drive.Name.Length -ne 1) { continue }
    if ($checked.ContainsKey($drive.Name)) { continue }
    $checked[$drive.Name] = $true
    $repo = "$($drive.Name):\saenggibu"
    if (Test-Path $repo) { return $repo }
  }
  return $null
}

function Sync-NasDeployScripts([hashtable]$Cfg) {
  $mappedRepo = Find-NasMappedRepo $Cfg
  if (-not $mappedRepo) {
    Write-Warn "SMB drive not mapped (no X:\saenggibu). Run: .\scripts\nas-pc.ps1 map -Profile local"
    return $false
  }

  $destDir = Join-Path $mappedRepo "scripts"
  if (-not (Test-Path $destDir)) {
    New-Item -ItemType Directory -Path $destDir | Out-Null
  }

  $files = @("nas-docker-update.sh", "nas-cleanup-example-samples.sh", "nas-scheduled-pull.sh", "nas-setup-docker-sudo.sh")
  foreach ($name in $files) {
    $src = Join-Path $Root "scripts\$name"
    if (-not (Test-Path $src)) { continue }
    Write-NasUnixFile $src (Join-Path $destDir $name)
  }

  Write-Ok "Synced deploy scripts (LF) -> $destDir"
  return $true
}

function Get-NasRemotePathPrefix {
  return 'export PATH="/usr/local/bin:/var/packages/ContainerManager/target/usr/bin:/var/packages/Docker/target/usr/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"'
}

function Sync-NasAdminUi([hashtable]$Cfg) {
  $mappedRepo = Find-NasMappedRepo $Cfg
  if (-not $mappedRepo) {
    Write-Warn "SMB drive not mapped. Run: .\scripts\nas-pc.ps1 map -Profile local"
    return $false
  }

  $src = Join-Path $Root "web\admin"
  $dest = Join-Path $mappedRepo "web\admin"
  if (-not (Test-Path $src)) {
    throw "Missing web\admin in repo"
  }
  if (-not (Test-Path $dest)) {
    New-Item -ItemType Directory -Path $dest -Force | Out-Null
  }

  Copy-Item -Path (Join-Path $src "*") -Destination $dest -Recurse -Force
  Write-Ok "Synced admin UI -> $dest"
  Write-Host "  Browser: Ctrl+F5 on sgb.mansejin.com"
  return $true
}

function Get-DeployBranch([hashtable]$Cfg) {
  if ($Cfg["NAS_DEPLOY_BRANCH"]) { return $Cfg["NAS_DEPLOY_BRANCH"] }
  try {
    $branch = & git -C $Root rev-parse --abbrev-ref HEAD 2>$null
    if ($LASTEXITCODE -eq 0 -and $branch -and $branch -ne "HEAD") {
      return $branch
    }
  } catch {}
  return "cursor/saenggibu-writer-5821"
}

function Escape-ShSingleQuoted([string]$Value) {
  return $Value -replace "'", "'\\''"
}

function Build-NasRemoteExports([hashtable]$Cfg) {
  $branch = Get-DeployBranch $Cfg
  $sudo = if ($Cfg["NAS_DOCKER_SUDO"]) { $Cfg["NAS_DOCKER_SUDO"] } else { "1" }
  $exports = "export SGB_DOCKER_SUDO=$sudo; export SGB_BRANCH='$branch'"
  if ($Cfg["NAS_SUDO_PASSWORD"]) {
    $pass = Escape-ShSingleQuoted $Cfg["NAS_SUDO_PASSWORD"]
    $exports += "; export NAS_SUDO_PASSWORD='$pass'"
  }
  return $exports
}

function Build-NasUpdateRemote([hashtable]$Cfg, [string]$Repo) {
  $pathPrefix = Get-NasRemotePathPrefix
  $remoteEnv = Build-NasRemoteExports $Cfg
  $branch = Escape-ShSingleQuoted (Get-DeployBranch $Cfg)
  $run = "curl -fsSL ""https://raw.githubusercontent.com/Mansejin/auto_script/$branch/scripts/nas-docker-update.sh"" -o /tmp/sgb-deploy.sh && sed -i 's/\r$//' /tmp/sgb-deploy.sh && cd '$Repo' && sh /tmp/sgb-deploy.sh"
  return "${pathPrefix}; ${remoteEnv}; $run"
}

function Copy-FileToNas([string]$Alias, [string]$LocalFile, [string]$RemoteFile) {
  $remoteParent = $RemoteFile -replace "/[^/]+$", ""
  if ($remoteParent) {
    & ssh $Alias "mkdir -p '$remoteParent'" | Out-Null
  }
  $exit = & cmd.exe /c "ssh $Alias `"cat > '$RemoteFile'`" < `"$LocalFile`""
  if ($exit -ne 0) {
    throw "Upload failed: $LocalFile -> $RemoteFile"
  }
}

function Copy-TreeToNas([string]$Alias, [string]$LocalDir, [string]$RemoteDir) {
  $files = Get-ChildItem -Path $LocalDir -Recurse -File
  if (-not $files.Count) {
    Write-Warn "  (empty) $LocalDir"
    return 0
  }
  $base = (Resolve-Path $LocalDir).Path.TrimEnd('\')
  $count = 0
  foreach ($file in $files) {
    $rel = $file.FullName.Substring($base.Length).TrimStart('\') -replace '\\', '/'
    $remotePath = "$RemoteDir/$rel"
    Copy-FileToNas $Alias $file.FullName $remotePath
    Write-Host "    $rel" -ForegroundColor DarkGray
    $count++
  }
  return $count
}

function Invoke-SyncData {
  $cfg = Get-NasConfig
  Ensure-OpenSsh
  $profile = Resolve-NasProfile $cfg $script:NasProfile
  $repo = $cfg["NAS_REPO_PATH"]
  $remoteData = "$repo/data/saenggibu"
  $localBase = Join-Path $Root "data\saenggibu"
  if (-not (Test-Path $localBase)) {
    throw "Missing local data: $localBase"
  }

  Write-Info "Sync local data -> NAS [$($profile.Label)] (file-by-file over SSH)"
  $total = 0
  foreach ($name in @("students", "samples", "outputs")) {
    $localPath = Join-Path $localBase $name
    if (-not (Test-Path $localPath)) {
      Write-Warn "Skip (missing): $name"
      continue
    }
    Write-Info "  -> $name"
    $total += Copy-TreeToNas $profile.Alias $localPath "$remoteData/$name"
  }

  $patterns = Join-Path $localBase "patterns.json"
  if (Test-Path $patterns) {
    Write-Info "  -> patterns.json"
    Copy-FileToNas $profile.Alias $patterns "$remoteData/patterns.json"
    $total++
  } else {
    Write-Warn "Skip (missing): patterns.json"
  }

  Write-Ok "Data sync finished ($total files). Verify: ssh $($profile.Alias) ls $remoteData/students"
}

function Invoke-NasDeploy {
  $cfg = Get-NasConfig
  Write-Info "Deploy: NAS git pull + docker rebuild (SSH)..."
  Write-Info "UI comes from git. sync-ui only for emergency hotfix."
  Invoke-NasUpdate
  Write-Ok "Deploy complete. Browser: Ctrl+F5 on sgb.mansejin.com"
}

function Invoke-NasUpdate {
  $cfg = Get-NasConfig
  $repo = $cfg["NAS_REPO_PATH"]
  $profile = Resolve-NasProfile $cfg $script:NasProfile
  Write-Info "NAS update [$($profile.Label)] -> $($profile.Host)..."
  Write-Info "Branch: $(Get-DeployBranch $cfg)"
  if (-not $cfg["NAS_SUDO_PASSWORD"]) {
    Write-Warn "No NAS_SUDO_PASSWORD in config — if docker fails, add ohola password to config/nas-pc.local.env"
    Write-Warn "Or run once on NAS as root: sh scripts/nas-setup-docker-sudo.sh"
  }
  Invoke-NasRemote (Build-NasUpdateRemote $cfg $repo)
  Write-Ok "Done"
}

function Invoke-NasLogs {
  $cfg = Get-NasConfig
  $repo = $cfg["NAS_REPO_PATH"]
  Sync-NasDeployScripts $cfg | Out-Null
  $pathPrefix = Get-NasRemotePathPrefix
  Invoke-NasRemote "${pathPrefix}; cd '$repo' && sh scripts/nas-docker-update.sh --logs-only"
}

function Get-FreeDriveLetter([string[]]$Prefer) {
  foreach ($l in $Prefer) {
    $l = $l.TrimEnd(":").ToUpper()
    if ($l.Length -ne 1) { continue }
    if (-not (Test-Path "${l}:\")) { return $l }
  }
  throw "No free drive letter. Unmap one: net use Z: /delete"
}

function Invoke-NasMap {
  $cfg = Get-NasConfig
  $profile = Resolve-NasProfile $cfg $script:NasProfile
  $letter = if ($DriveLetter) { $DriveLetter.TrimEnd(":").ToUpper() } else { $cfg["NAS_DRIVE_LETTER"].TrimEnd(":").ToUpper() }
  $unc = "\\$($profile.SmbHost)\$($cfg['NAS_SMB_SHARE'])"

  if (Test-Path "${letter}:\") {
    $current = (Get-PSDrive -Name $letter -PSProvider FileSystem -ErrorAction SilentlyContinue).DisplayRoot
    if ($current -eq $unc) {
      Write-Ok "Already mapped: ${letter}: -> $unc"
      Write-Host "  Open: ${letter}:\saenggibu"
      return
    }
    Write-Warn "Drive ${letter}: is used by something else."
    $letter = Get-FreeDriveLetter @("Y", "X", "W", "V", "U", "T", "S")
    Write-Info "Trying ${letter}: instead. Set NAS_DRIVE_LETTER=$letter in config/nas-pc.local.env"
  }

  Write-Info "SMB [$($profile.Label)]: $unc -> ${letter}:"
  cmd /c "net use ${letter}: `"$unc`" /persistent:yes"
  if ($LASTEXITCODE -ne 0) {
    throw "SMB failed. Check DSM shared folder 'docker' and SMB enabled."
  }
  Write-Ok "Mapped ${letter}: -> $unc"
  Write-Host "  Open: ${letter}:\saenggibu"
}

function Invoke-NasUnmap {
  $cfg = Get-NasConfig
  $letter = $cfg["NAS_DRIVE_LETTER"].TrimEnd(":")
  cmd /c "net use ${letter}: /delete /y"
  Write-Ok "Unmapped ${letter}:"
}

function Test-SshProfile([hashtable]$Cfg, [string]$ProfileName) {
  $target = Resolve-NasProfile $Cfg $ProfileName
  $sshOpts = Build-SshArgs $Cfg
  $hostAddr = "$($Cfg['NAS_USER'])@$($target.Host)"
  & ssh @sshOpts -o BatchMode=yes $hostAddr "echo ok" 2>$null
  return ($LASTEXITCODE -eq 0)
}

function Get-IcaclsPrincipals([string]$Path) {
  $principals = @()
  $raw = & icacls $Path 2>$null
  foreach ($line in $raw) {
    if ($line -match '^\s+(.+?):\([^)]*\)\s*$') {
      $principals += $Matches[1].Trim()
    }
  }
  return $principals
}

function Repair-IcaclsPrivate([string]$Path) {
  if (-not (Test-Path $Path)) { return }
  icacls $Path /reset | Out-Null
  icacls $Path /inheritance:r | Out-Null
  $me = (& whoami).Trim()
  foreach ($principal in (Get-IcaclsPrincipals $Path)) {
    if ($principal -ne $me -and $principal -ne $env:USERNAME) {
      icacls $Path /remove $principal 2>$null | Out-Null
    }
  }
  icacls $Path /grant:r "${env:USERNAME}:F" | Out-Null
}

function Repair-IcaclsDir([string]$Path) {
  if (-not (Test-Path $Path)) { return }
  icacls $Path /inheritance:r | Out-Null
  $me = (& whoami).Trim()
  foreach ($principal in (Get-IcaclsPrincipals $Path)) {
    if ($principal -ne $me -and $principal -ne $env:USERNAME) {
      icacls $Path /remove $principal 2>$null | Out-Null
    }
  }
  icacls $Path /grant:r "${env:USERNAME}:(OI)(CI)F" | Out-Null
}

function Invoke-FixSshPerms {
  $sshDir = Join-Path $env:USERPROFILE ".ssh"
  $config = Join-Path $sshDir "config"
  if (-not (Test-Path $sshDir)) { New-Item -ItemType Directory -Path $sshDir | Out-Null }

  if (Test-Path $config) {
    Repair-IcaclsPrivate $config
    Write-Ok "Fixed: $config"
  } else {
    Write-Warn "No config file yet."
  }

  Repair-IcaclsDir $sshDir

  $keyPath = Join-Path $sshDir "id_ed25519"
  if (Test-Path $keyPath) { Fix-SshKeyPerms $keyPath }

  Write-Ok "Try: ssh saenggibu-nas-local"
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
  Rewrite-AllSshConfigs $cfg | Out-Null

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
    "deploy" { Invoke-NasDeploy }
    "logs" { Invoke-NasLogs }
    "map" { Invoke-NasMap }
    "unmap" { Invoke-NasUnmap }
    "status" { Invoke-NasStatus }
    "fix-ssh" { Invoke-FixSshPerms }
    "install-key" { Invoke-InstallKey }
    "sync-ui" {
      $cfg = Get-NasConfig
      Sync-NasAdminUi $cfg | Out-Null
    }
    "sync-data" { Invoke-SyncData }
  }
} catch {
  Write-Host ""
  Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
  exit 1
}
