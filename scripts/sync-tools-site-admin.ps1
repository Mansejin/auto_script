# deploy/tools-site-admin → tools-site 저장소로 복사 (Windows PowerShell)
param(
    [Parameter(Mandatory = $true)]
    [string]$ToolsSitePath
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Src = Join-Path $Root "deploy\tools-site-admin"
$Dest = Join-Path $ToolsSitePath "admin\saenggibu"

if (-not (Test-Path $ToolsSitePath)) {
    Write-Error "tools-site 경로가 없습니다: $ToolsSitePath"
}

New-Item -ItemType Directory -Force -Path $Dest | Out-Null
Copy-Item -Path (Join-Path $Src "admin\saenggibu\*") -Destination $Dest -Recurse -Force

$robotsSnippet = Join-Path $Src "robots.txt.snippet"
$robotsDest = Join-Path $ToolsSitePath "robots.txt"
$snippetText = Get-Content $robotsSnippet -Raw

if (Test-Path $robotsDest) {
    $existing = Get-Content $robotsDest -Raw
    if ($existing -notmatch "Disallow:\s*/admin/") {
        Add-Content -Path $robotsDest -Value "`n$snippetText"
        Write-Host "robots.txt 에 /admin/ Disallow 추가됨"
    }
} else {
    Set-Content -Path $robotsDest -Value $snippetText.TrimEnd()
    Write-Host "robots.txt 생성됨"
}

Write-Host "복사 완료: $Dest"
