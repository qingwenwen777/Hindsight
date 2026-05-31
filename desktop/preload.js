"use strict";

/**
 * Preload：在页面脚本运行前，把后端地址注入到 window。
 * 前端的 getApiBase() 会优先读取 window.__TRADEAI_API_BASE__。
 *
 * 后端端口是启动时动态分配的，主进程通过环境变量 TRADEAI_API_BASE 传过来。
 */

const { contextBridge, ipcRenderer } = require("electron");

const apiBase = process.env.TRADEAI_API_BASE || "http://127.0.0.1:8000";

// contextIsolation 下用 contextBridge 暴露到主世界
contextBridge.exposeInMainWorld("__TRADEAI_API_BASE__", apiBase);

// 自动更新桥：前端通过 window.tradeaiUpdater 调用主进程并监听事件
const updateListeners = new Map();
const VALID_EVENTS = [
  "update:available",
  "update:none",
  "update:error",
  "update:progress",
  "update:downloaded",
];

for (const ch of VALID_EVENTS) {
  ipcRenderer.on(ch, (_e, payload) => {
    const set = updateListeners.get(ch);
    if (set) set.forEach((cb) => cb(payload));
  });
}

contextBridge.exposeInMainWorld("tradeaiUpdater", {
  // 是否运行在桌面客户端（Web 部署时为 undefined）
  isDesktop: true,
  check: () => ipcRenderer.invoke("update:check"),
  download: () => ipcRenderer.invoke("update:download"),
  install: () => ipcRenderer.invoke("update:install"),
  // 订阅事件，返回取消订阅函数
  on: (event, cb) => {
    if (!VALID_EVENTS.includes(event)) return () => {};
    if (!updateListeners.has(event)) updateListeners.set(event, new Set());
    updateListeners.get(event).add(cb);
    return () => updateListeners.get(event)?.delete(cb);
  },
});
