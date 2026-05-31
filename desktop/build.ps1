# TradeAI 桌面客户端 —— Windows 一键打包脚本
#
# 流程：
#   1. 构建前端（Next standalone）
#   2. 用 PyInstaller 打包后端为 exe
#   3. 组装资源到 desktop/resources
#   4. 生成图标
#   5. electron-builder 打 NSIS 安装包
#
# 用法（在 desktop/ 目录）：  ./build.ps1
# 前置：backend/.venv 已装依赖（含 pyinstaller、pillow），desktop/ 已 npm install。

$ErrorActionPreference = "Stop"
$desktop = $PSScriptRoot
$root = Split-Path $desktop -Parent
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$py = Join-Path $backend ".venv\Scripts\python.exe"

Write-Host "==> [1/5] 构建前端 (Next standalone)" -ForegroundColor Cyan
Push-Location $frontend
npm run build
Pop-Location

Write-Host "==> [2/5] 打包后端 (PyInstaller)" -ForegroundColor Cyan
Push-Location $backend
& $py -m PyInstaller desktop.spec --noconfirm --distpath dist_desktop --workpath build_desktop
Pop-Location

Write-Host "==> [3/5] 生成图标" -ForegroundColor Cyan
& $py (Join-Path $desktop "scripts\make_icon.py")

Write-Host "==> [4/5] 组装资源" -ForegroundColor Cyan
Push-Location $desktop
node scripts/prepare-resources.mjs

Write-Host "==> [5/5] 打 NSIS 安装包 (electron-builder)" -ForegroundColor Cyan
npx electron-builder --win --x64
Pop-Location

Write-Host "==> 完成。安装包见 desktop/dist/" -ForegroundColor Green
