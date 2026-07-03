# Remove example samples from NAS data (ASCII-only for PowerShell 5.1)
# Usage:
#   .\scripts\nas-cleanup-example-samples.ps1
#   .\scripts\nas-cleanup-example-samples.ps1 -SamplesDir "T:\saenggibu\data\saenggibu\samples"
#   .\scripts\nas-cleanup-example-samples.ps1 -Id sample2cddc746

param(
  [string]$SamplesDir = "",
  [string]$Id = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$LocalConfig = Join-Path $Root "config\nas-pc.local.env"

function Get-ConfigDriveLetter {
  if (-not (Test-Path $LocalConfig)) { return "" }
  foreach ($line in Get-Content $LocalConfig -Encoding UTF8) {
    if ($line -match '^NAS_DRIVE_LETTER=(.+)$') {
      return $Matches[1].Trim().TrimEnd(':')
    }
  }
  return ""
}

function Find-SamplesDir([string]$Explicit) {
  if ($Explicit) {
    $index = Join-Path $Explicit "index.json"
    if (Test-Path $index) { return $Explicit }
  }

  $letters = @('T', 'Y', 'X', 'W', 'V', 'U', 'S', 'Z')
  $cfgLetter = Get-ConfigDriveLetter
  if ($cfgLetter) { $letters = @($cfgLetter) + ($letters | Where-Object { $_ -ne $cfgLetter }) }

  $suffixes = @(
    '\saenggibu\data\saenggibu\samples',
    '\data\saenggibu\samples'
  )

  $candidates = @()
  foreach ($letter in $letters) {
    if (-not (Test-Path "${letter}:\")) { continue }
    foreach ($suffix in $suffixes) {
      $candidates += "${letter}:$suffix"
    }
  }

  foreach ($path in $candidates) {
    if (Test-Path (Join-Path $path "index.json")) {
      return $path
    }
  }
  return ""
}

if (-not $SamplesDir) {
  $SamplesDir = Find-SamplesDir ""
} else {
  $resolved = Find-SamplesDir $SamplesDir
  if ($resolved) { $SamplesDir = $resolved }
}

if (-not $SamplesDir) {
  Write-Host "Could not find data/saenggibu/samples on mapped drives."
  Write-Host ""
  Write-Host "1) Map NAS docker share, e.g.:"
  Write-Host "     net use T: \\169.254.158.191\docker"
  Write-Host "2) Check path in Explorer (one of these):"
  Write-Host "     T:\saenggibu\data\saenggibu\samples"
  Write-Host "     T:\data\saenggibu\samples"
  Write-Host "3) Run with full path:"
  Write-Host "     .\scripts\nas-cleanup-example-samples.ps1 -SamplesDir `"T:\...\samples`""
  throw "samples folder not found"
}

Write-Host "Using: $SamplesDir"
$indexPath = Join-Path $SamplesDir "index.json"

function Test-ExampleSample([object]$item) {
  if ($Id -and $item.id -eq $Id) { return $true }
  $label = [string]$item.label
  $source = [string]$item.source_file
  if ($label -match '^2025_') { return $true }
  if ($source -match 'examples[/\\]sample_[ab]\.') { return $true }
  if ($source -match 'saenggibu-samples\.example') { return $true }
  return $false
}

$raw = Get-Content $indexPath -Raw -Encoding UTF8
$items = $raw | ConvertFrom-Json
if ($items -isnot [Array]) { $items = @($items) }

$remove = @($items | Where-Object { Test-ExampleSample $_ })
$keep = @($items | Where-Object { -not (Test-ExampleSample $_) })

if (-not $remove.Count) {
  Write-Host "No example samples to remove."
  exit 0
}

Write-Host "Will remove $($remove.Count) sample(s):"
foreach ($r in $remove) {
  Write-Host "  - $($r.label) ($($r.id))"
}

$confirm = Read-Host "Delete? (y/N)"
if ($confirm -notmatch '^[yY]$') {
  Write-Host "Cancelled."
  exit 0
}

foreach ($r in $remove) {
  $file = Join-Path $SamplesDir "$($r.id).json"
  if (Test-Path $file) { Remove-Item $file -Force }
}

$json = $keep | ConvertTo-Json -Depth 20
if ($keep.Count -eq 1) {
  $json = "[$json]"
}
Set-Content $indexPath -Value $json -Encoding UTF8
Write-Host "Done. $($keep.Count) sample(s) left."
