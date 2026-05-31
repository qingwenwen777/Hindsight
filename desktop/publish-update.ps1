# Publish a new release to the self-hosted update server (electron-updater generic provider).
#
# After electron-builder, dist/ contains:
#   - "TradeAI Setup <ver>.exe"   installer
#   - latest.yml                  update manifest (electron-updater reads this)
#   - *.exe.blockmap              differential download
#
# This uploads them to <RemoteDir>/updates on the server, matching the feed URL
# http://154.36.185.85:8090/updates/.
#
# Usage:  ./publish-update.ps1

param(
    [string]$Server = "root@154.36.185.85",
    [string]$RemoteDir = "/opt/tradeai-updates/updates",
    [string]$DistDir = "$PSScriptRoot\dist"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path "$DistDir\latest.yml")) {
    Write-Error "latest.yml not found in $DistDir. Run the build first."
}

Write-Host "==> ensuring remote dir: $RemoteDir"
ssh $Server "mkdir -p $RemoteDir"

# Upload installer + blockmap first, latest.yml last (so clients never see a
# manifest pointing at a not-yet-uploaded file).
$exe = Get-ChildItem "$DistDir\*.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Write-Host "==> uploading $($exe.Name)"
scp $exe.FullName "${Server}:$RemoteDir/"

Get-ChildItem "$DistDir\*.blockmap" -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "==> uploading $($_.Name)"
    scp $_.FullName "${Server}:$RemoteDir/"
}

Write-Host "==> uploading latest.yml"
scp "$DistDir\latest.yml" "${Server}:$RemoteDir/"

Write-Host "==> done. Feed: http://154.36.185.85:8090/updates/"
