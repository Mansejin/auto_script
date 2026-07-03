# web/admin → deploy/tools-site-admin (mansejin.com GitHub Pages용)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Src = Join-Path $Root "web\admin"
$Dest = Join-Path $Root "deploy\tools-site-admin\admin\saenggibu"

New-Item -ItemType Directory -Force -Path $Dest | Out-Null
Copy-Item -Path (Join-Path $Src "css") -Destination $Dest -Recurse -Force
Copy-Item -Path (Join-Path $Src "js") -Destination $Dest -Recurse -Force
Copy-Item -Path (Join-Path $Src "samples") -Destination $Dest -Recurse -Force

$html = Get-Content (Join-Path $Src "index.html") -Raw -Encoding UTF8
$html = $html -replace 'href="/admin-static/css/', 'href="css/'
$html = $html -replace 'src="/admin-static/js/', 'src="js/'
$html = $html -replace 'data-api-base="" data-assets-base="/admin-static"', 'data-api-base="https://sgb.mansejin.com" data-assets-base=""'
[System.IO.File]::WriteAllText((Join-Path $Dest "index.html"), $html, [System.Text.UTF8Encoding]::new($false))

Write-Host "deploy 번들 갱신: $Dest"
