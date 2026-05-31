# 发布更新到自有服务器（electron-updater generic provider）
#
# electron-builder 打包后会在 dist/ 生成：
#   - TradeAI Setup <版本>.exe   安装包
#   - latest.yml                 版本清单（electron-updater 据此判断有无更新）
#   - *.exe.blockmap             增量下载用
#
# 本脚本把这三类文件上传到服务器的 /opt/tradeai-updates（对应 http://<host>:8080/updates/）。
#
# 用法：./publish-update.ps1 -Server root@154.36.185.85

param(
    [string]$Server = "root@154.36.185.85",
    [string]$RemoteDir = "/opt/tradeai-updates",
    [string]$DistDir = "$PSScriptRoot\dist"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path "$DistDir\latest.yml")) {
    Write-Error "未找到 $DistDir\latest.yml，请先运行打包（build.ps1）。"
}

Write-Host "==> 确保服务器目录存在：$RemoteDir"
ssh $Server "mkdir -p $RemoteDir"

Write-Host "==> 上传安装包与清单"
# latest.yml 必须最后上传，确保客户端读到时对应的 exe 已就绪
$exe = Get-ChildItem "$DistDir\*.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
scp $exe.FullName "${Server}:$RemoteDir/"
Get-ChildItem "$DistDir\*.blockmap" -ErrorAction SilentlyContinue | ForEach-Object {
    scp $_.FullName "${Server}:$RemoteDir/"
}
scp "$DistDir\latest.yml" "${Server}:$RemoteDir/"

Write-Host "==> 完成。更新源：http://154.36.185.85:8090/updates/" -ForegroundColor Green
