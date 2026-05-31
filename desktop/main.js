"use strict";

/**
 * TradeAI 桌面客户端主进程。
 *
 * 启动流程：
 * 1. 选两个空闲端口（后端、前端）。
 * 2. 拉起打包好的后端 exe（PyInstaller 产物，含 Python 运行时）。
 * 3. 用 Electron 内置 Node 拉起 Next standalone 前端服务。
 * 4. 等两者就绪后，窗口加载前端，并通过 preload 注入后端地址。
 *
 * 退出时确保两个子进程都被杀掉，避免残留。
 */

const { app, BrowserWindow, dialog, shell } = require("electron");
const { autoUpdater } = require("electron-updater");
const { spawn } = require("node:child_process");
const http = require("node:http");
const net = require("node:net");
const path = require("node:path");
const fs = require("node:fs");

const isDev = !app.isPackaged;

// 资源根：打包后在 process.resourcesPath/{backend,frontend}；开发期在 ./resources
const resourcesRoot = isDev
  ? path.join(__dirname, "resources")
  : process.resourcesPath;

const BACKEND_DIR = path.join(resourcesRoot, "backend");
const FRONTEND_DIR = path.join(resourcesRoot, "frontend");
const BACKEND_EXE = path.join(BACKEND_DIR, "tradeai-backend.exe");
const FRONTEND_SERVER = path.join(FRONTEND_DIR, "server.js");

/** @type {import('child_process').ChildProcess | null} */
let backendProc = null;
/** @type {import('child_process').ChildProcess | null} */
let frontendProc = null;
/** @type {BrowserWindow | null} */
let mainWindow = null;
let shuttingDown = false;

/** 找一个空闲 TCP 端口。 */
function getFreePort() {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.unref();
    srv.on("error", reject);
    srv.listen(0, "127.0.0.1", () => {
      const { port } = srv.address();
      srv.close(() => resolve(port));
    });
  });
}

/** 轮询 HTTP 直到返回任意响应或超时。 */
function waitForHttp(url, { timeoutMs = 60000, intervalMs = 400 } = {}) {
  const deadline = Date.now() + timeoutMs;
  return new Promise((resolve, reject) => {
    const tick = () => {
      const req = http.get(url, (res) => {
        res.destroy();
        resolve(true);
      });
      req.on("error", () => {
        if (Date.now() > deadline) {
          reject(new Error(`等待服务就绪超时：${url}`));
        } else {
          setTimeout(tick, intervalMs);
        }
      });
      req.setTimeout(2000, () => req.destroy());
    };
    tick();
  });
}

/** 把日志写到用户数据目录，便于排查。 */
function logLine(msg) {
  try {
    const logDir = app.getPath("userData");
    fs.appendFileSync(
      path.join(logDir, "desktop.log"),
      `[${new Date().toISOString()}] ${msg}\n`,
    );
  } catch {
    /* 忽略日志写入失败 */
  }
}

function startBackend(port) {
  logLine(`启动后端 ${BACKEND_EXE} 端口 ${port}`);
  const proc = spawn(BACKEND_EXE, [String(port)], {
    cwd: BACKEND_DIR,
    env: { ...process.env, TRADEAI_HOST: "127.0.0.1", TRADEAI_PORT: String(port) },
    windowsHide: true,
  });
  proc.stdout.on("data", (d) => logLine(`[backend] ${d.toString().trim()}`));
  proc.stderr.on("data", (d) => logLine(`[backend] ${d.toString().trim()}`));
  proc.on("exit", (code) => {
    logLine(`后端进程退出 code=${code}`);
    if (!shuttingDown) handleChildCrash("后端");
  });
  return proc;
}

function startFrontend(port, apiBase) {
  logLine(`启动前端 ${FRONTEND_SERVER} 端口 ${port}`);
  const proc = spawn(process.execPath, [FRONTEND_SERVER], {
    cwd: FRONTEND_DIR,
    env: {
      ...process.env,
      // 让 Electron 的内置 Node 以纯 Node 方式运行 server.js
      ELECTRON_RUN_AS_NODE: "1",
      PORT: String(port),
      HOSTNAME: "127.0.0.1",
      NODE_ENV: "production",
      NEXT_PUBLIC_API_URL: apiBase,
    },
    windowsHide: true,
  });
  proc.stdout.on("data", (d) => logLine(`[frontend] ${d.toString().trim()}`));
  proc.stderr.on("data", (d) => logLine(`[frontend] ${d.toString().trim()}`));
  proc.on("exit", (code) => {
    logLine(`前端进程退出 code=${code}`);
    if (!shuttingDown) handleChildCrash("前端");
  });
  return proc;
}

function handleChildCrash(which) {
  if (shuttingDown) return;
  dialog.showErrorBox("TradeAI", `${which}服务意外退出，应用将关闭。日志见用户数据目录 desktop.log。`);
  cleanup();
  app.quit();
}

/**
 * 自动更新：从自有服务器（generic provider）检查更新。
 * 发现新版本 -> 静默后台下载 -> 下载完成提示用户重启安装。
 * 不强制，用户可稍后再说；失败只记日志，不打断使用。
 */
function setupAutoUpdater() {
  if (isDev) return; // 开发期不检查

  autoUpdater.autoDownload = true;
  autoUpdater.autoInstallOnAppQuit = true;
  autoUpdater.logger = { info: logLine, warn: logLine, error: logLine, debug: () => {} };

  autoUpdater.on("update-available", (info) => {
    logLine(`发现新版本 ${info.version}，后台下载中`);
  });
  autoUpdater.on("update-not-available", () => {
    logLine("已是最新版本");
  });
  autoUpdater.on("error", (err) => {
    logLine(`更新检查失败：${err == null ? "unknown" : err.message || err}`);
  });
  autoUpdater.on("update-downloaded", async (info) => {
    logLine(`新版本 ${info.version} 下载完成`);
    if (!mainWindow) return;
    const { response } = await dialog.showMessageBox(mainWindow, {
      type: "info",
      buttons: ["立即重启更新", "稍后"],
      defaultId: 0,
      cancelId: 1,
      title: "发现新版本",
      message: `TradeAI ${info.version} 已下载完成`,
      detail: "是否立即重启以完成更新？也可以稍后退出时自动安装。",
    });
    if (response === 0) {
      shuttingDown = true;
      cleanup();
      autoUpdater.quitAndInstall();
    }
  });

  // 启动后延迟检查，避开启动高峰
  setTimeout(() => {
    autoUpdater.checkForUpdates().catch((e) => logLine(`checkForUpdates 异常：${e}`));
  }, 8000);
}

function killProc(proc) {
  if (!proc || proc.killed) return;
  try {
    // Windows 下用 taskkill 确保子进程树被清理
    if (process.platform === "win32" && proc.pid) {
      spawn("taskkill", ["/pid", String(proc.pid), "/f", "/t"], { windowsHide: true });
    } else {
      proc.kill();
    }
  } catch (e) {
    logLine(`结束进程失败：${e}`);
  }
}

function cleanup() {
  shuttingDown = true;
  killProc(backendProc);
  killProc(frontendProc);
  backendProc = null;
  frontendProc = null;
}

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 680,
    backgroundColor: "#ffffff",
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // 启动加载页
  await mainWindow.loadFile(path.join(__dirname, "splash.html"));
  mainWindow.show();

  // 外部链接用系统浏览器打开
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith("http")) {
      shell.openExternal(url);
      return { action: "deny" };
    }
    return { action: "allow" };
  });

  try {
    const [backendPort, frontendPort] = await Promise.all([getFreePort(), getFreePort()]);
    const apiBase = `http://127.0.0.1:${backendPort}`;
    const frontendUrl = `http://127.0.0.1:${frontendPort}`;

    // 把后端地址通过环境变量传给 preload（preload 无法直接读主进程变量）
    process.env.TRADEAI_API_BASE = apiBase;

    backendProc = startBackend(backendPort);
    frontendProc = startFrontend(frontendPort, apiBase);

    await Promise.all([
      waitForHttp(`${apiBase}/health`, { timeoutMs: 90000 }),
      waitForHttp(frontendUrl, { timeoutMs: 90000 }),
    ]);

    logLine("前后端就绪，加载窗口");
    await mainWindow.loadURL(frontendUrl);

    // 窗口就绪后再检查更新
    setupAutoUpdater();
  } catch (e) {
    logLine(`启动失败：${e}`);
    dialog.showErrorBox("TradeAI 启动失败", String(e && e.message ? e.message : e));
    cleanup();
    app.quit();
  }
}

// 单实例锁，避免多开导致端口/数据库竞争
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });

  app.whenReady().then(createWindow);

  app.on("window-all-closed", () => {
    cleanup();
    app.quit();
  });

  app.on("before-quit", cleanup);
  app.on("quit", cleanup);
}
