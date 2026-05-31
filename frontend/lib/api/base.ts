/**
 * 解析后端 API 基址。
 *
 * 优先级：
 * 1. 运行时注入（桌面版 Electron 通过 preload 设置 window.__TRADEAI_API_BASE__，
 *    因为端口是启动时动态分配的，构建期无法写死）。
 * 2. 构建期环境变量 NEXT_PUBLIC_API_URL（Web/Docker 部署）。
 * 3. 兜底 localhost:8000（本地开发）。
 */

declare global {
  interface Window {
    __TRADEAI_API_BASE__?: string;
  }
}

const BUILD_TIME_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function getApiBase(): string {
  if (typeof window !== "undefined" && window.__TRADEAI_API_BASE__) {
    return window.__TRADEAI_API_BASE__;
  }
  return BUILD_TIME_BASE;
}
