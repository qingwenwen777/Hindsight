"use strict";

/**
 * Preload：在页面脚本运行前，把后端地址注入到 window。
 * 前端的 getApiBase() 会优先读取 window.__TRADEAI_API_BASE__。
 *
 * 后端端口是启动时动态分配的，主进程通过环境变量 TRADEAI_API_BASE 传过来。
 */

const { contextBridge } = require("electron");

const apiBase = process.env.TRADEAI_API_BASE || "http://127.0.0.1:8000";

// contextIsolation 下用 contextBridge 暴露到主世界
contextBridge.exposeInMainWorld("__TRADEAI_API_BASE__", apiBase);
