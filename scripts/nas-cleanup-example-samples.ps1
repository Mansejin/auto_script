# Remove example samples from NAS data (ASCII-only for PowerShell 5.1)
# Usage:
#   .\scripts\nas-cleanup-example-samples.ps1
#   .\scripts\nas-cleanup-example-samples.ps1 -SamplesDir "T:\saenggibu\data\saenggibu\samples"
#   .\scripts\nas-cleanup-example-samples.ps1 -Id sample2cddc746

param(
  [string]$SamplesDir = "T:\saenggibu\data\saenggibu\samples",
  [string]$Id = ""
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $SamplesDir)) {
  throw "Folder not found: $SamplesDir`nMap T: first or set -SamplesDir"
}

$indexPath = Join-Path $SamplesDir "index.json"
if (-not (Test-Path $indexPath)) {
  throw "index.json not found in $SamplesDir"
}

function Test-ExampleSample([object]$item) {
  if ($Id -and $item.id -eq $Id) { return $true }
  $label = [string]$item.label
  $source = [string]$item.source_file
  # Built-in demo labels like 2025_2..._sampleB (any script)
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
