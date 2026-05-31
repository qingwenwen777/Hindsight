# TradeAI 桌面客户端（Windows）

把 TradeAI（Next.js 前端 + FastAPI/SQLite 后端）打包成 Windows 桌面应用。
用户下载安装包安装即可，无需 Python/Node 环境，所有数据与行情拉取都在本机进行。

## 架构

```
TradeAI.exe (Electron 主进程)
├── 启动时选两个空闲端口
├── 拉起 tradeai-backend.exe         （PyInstaller 打包，含 Python 运行时）
│     └── 监听 127.0.0.1:<后端端口>，进程内跑 alembic 迁移
├── 用 Electron 内置 Node 拉起 Next standalone server.js
│     └── 监听 127.0.0.1:<前端端口>
└── 窗口加载前端，preload 注入后端地址 (window.__TRADEAI_API_BASE__)
```

- **数据库**：`%APPDATA%/TradeAI/data/stock.db`（覆盖安装不丢数据）
- **运行日志**：`%APPDATA%/tradeai-desktop/desktop.log`
- **退出**：主进程负责杀掉后端/前端子进程（taskkill /t）

## 目录

```
desktop/
├── main.js                     Electron 主进程（编排前后端 + 窗口）
├── preload.js                  注入后端地址到前端
├── splash.html                 启动加载页
├── build.ps1                   一键打包脚本
├── scripts/
│   ├── prepare-resources.mjs   组装 resources/{backend,frontend}
│   └── make_icon.py            生成 build/icon.ico
├── build/icon.ico              应用图标（生成物）
├── resources/                  打包前组装的前后端产物（生成物，gitignore）
└── dist/                       electron-builder 输出（生成物，gitignore）
```

## 打包步骤

前置（各一次）：

```powershell
# 后端依赖（含打包工具）
cd backend
.venv\Scripts\python.exe -m pip install -e ".[desktop]"
.venv\Scripts\python.exe -m pip install pillow   # 生成图标用

# 桌面端依赖
cd ../desktop
npm install
```

一键打包：

```powershell
cd desktop
./build.ps1
```

产物：`desktop/dist/TradeAI Setup 0.1.0.exe`（NSIS 安装包）。
也可直接运行免安装版：`desktop/dist/win-unpacked/TradeAI.exe`。

## 开发调试

不重新打包、快速验证编排逻辑：

```powershell
# 先确保 resources/ 已组装（build.ps1 的前 4 步，或单独跑）
cd desktop
node scripts/prepare-resources.mjs
npm start
```

## 已知事项

- **首次启动**：需几秒拉起两个子进程并跑迁移，有启动加载页。
- **akshare 数据源**：sina 源依赖 py_mini_racer 原生库（已在 spec 收集）；
  即便某源失败，akshare/yfinance 有多源容错链路自动回退。
- **代码签名**：当前未签名，Windows SmartScreen 首次运行会提示。
  正式分发建议购买代码签名证书并在 electron-builder 配置。
- **体积**：安装后约 600MB+（含 Python 运行时 + scipy/pandas + Electron）。
- **electron-builder + winCodeSign**：若打包报 “Cannot create symbolic link”，
  是 winCodeSign 包内 macOS 符号链接在 Windows 无权限创建所致。手动解压并排除
  darwin 目录到缓存即可：
  `7za x <cache>\winCodeSign\*.7z -o<cache>\winCodeSign\winCodeSign-2.6.0 -xr!darwin`。
```
