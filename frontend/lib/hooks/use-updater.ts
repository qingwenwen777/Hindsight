"use client";

import { useEffect } from "react";

import { create } from "zustand";

/**
 * 桌面端自动更新状态（通过 preload 暴露的 window.tradeaiUpdater 桥接 Electron 主进程）。
 *
 * 流程：检查 -> available 弹窗询问 -> 用户点下载 -> progress 进度条 ->
 * downloaded 弹"重启安装"。用户暂不更新则保留 available 状态，左上角显示更新标识。
 */

export type UpdatePhase = "idle" | "available" | "downloading" | "downloaded" | "error";

interface UpdaterBridge {
  isDesktop: boolean;
  check: () => Promise<{ ok: boolean; message?: string }>;
  download: () => Promise<{ ok: boolean; message?: string }>;
  install: () => Promise<{ ok: boolean }>;
  on: (event: string, cb: (payload: unknown) => void) => () => void;
}

function bridge(): UpdaterBridge | null {
  if (typeof window === "undefined") return null;
  return (window as unknown as { tradeaiUpdater?: UpdaterBridge }).tradeaiUpdater ?? null;
}

interface UpdaterState {
  /** 是否在桌面客户端中运行（Web 部署时为 false，相关 UI 不渲染）。 */
  isDesktop: boolean;
  phase: UpdatePhase;
  version: string | null;
  notes: string | null;
  percent: number;
  bytesPerSecond: number;
  errorMessage: string | null;
  /** 弹窗是否打开（用户点左上角标识可重新打开）。 */
  dialogOpen: boolean;

  setState: (patch: Partial<UpdaterState>) => void;
  openDialog: () => void;
  closeDialog: () => void;
  startDownload: () => void;
  install: () => void;
}

export const useUpdaterStore = create<UpdaterState>((set, get) => ({
  isDesktop: false,
  phase: "idle",
  version: null,
  notes: null,
  percent: 0,
  bytesPerSecond: 0,
  errorMessage: null,
  dialogOpen: false,

  setState: (patch) => set(patch),
  openDialog: () => set({ dialogOpen: true }),
  closeDialog: () => set({ dialogOpen: false }),
  startDownload: () => {
    const b = bridge();
    if (!b) return;
    set({ phase: "downloading", percent: 0, errorMessage: null });
    b.download();
  },
  install: () => {
    const b = bridge();
    if (!b) return;
    b.install();
  },
}));

/** 在应用根部挂载一次，订阅主进程的更新事件。 */
export function useUpdaterBridge() {
  const setState = useUpdaterStore((s) => s.setState);

  useEffect(() => {
    const b = bridge();
    if (!b) return; // 非桌面环境
    setState({ isDesktop: true });

    const offs = [
      b.on("update:available", (p) => {
        const info = p as { version: string; notes: string | null };
        setState({
          phase: "available",
          version: info.version,
          notes: info.notes,
          dialogOpen: true,
        });
      }),
      b.on("update:none", () => {
        // 仅在用户手动检查时有意义；自动检查无新版静默处理
      }),
      b.on("update:progress", (p) => {
        const info = p as { percent: number; bytesPerSecond: number };
        setState({
          phase: "downloading",
          percent: Math.round(info.percent),
          bytesPerSecond: info.bytesPerSecond,
        });
      }),
      b.on("update:downloaded", () => {
        setState({ phase: "downloaded", percent: 100, dialogOpen: true });
      }),
      b.on("update:error", (p) => {
        const info = p as { message: string };
        setState({ phase: "error", errorMessage: info.message });
      }),
    ];

    return () => offs.forEach((off) => off && off());
  }, [setState]);
}
