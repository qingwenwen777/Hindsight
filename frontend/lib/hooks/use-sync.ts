"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getApiBase } from "@/lib/api/base";
import { api } from "@/lib/api/client";

export interface SyncSettings {
  auto_sync_enabled: boolean;
  scheduler_running: boolean;
  last_sync_at: string | null;
}

export interface SyncAllResult {
  stocks: number;
  by_market: Record<string, number>;
  inserted: number;
  updated: number;
  failed: { symbol: string; message: string }[];
}

export interface SyncedStock {
  stock_id: number;
  symbol: string;
  name: string;
  market: string;
  currency: string;
  bars: number;
  first_date: string | null;
  last_date: string | null;
}

/** 读取行情同步设置（自动更新开关 + 上次同步时间 + 调度是否启用）。 */
export function useSyncSettings() {
  return useQuery({
    queryKey: ["sync-settings"],
    queryFn: async () => (await api.get<SyncSettings>("/admin/sync/settings")).data,
  });
}

/** 开/关每日自动更新。 */
export function useUpdateSyncSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (autoSyncEnabled: boolean) =>
      (await api.put<{ auto_sync_enabled: boolean }>("/admin/sync/settings", {
        auto_sync_enabled: autoSyncEnabled,
      })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sync-settings"] }),
  });
}

/** 立即同步所有已录入股票（手动一键更新）。 */
export function useSyncAll() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => (await api.post<SyncAllResult>("/admin/sync/all")).data,
    onSuccess: () => {
      // 同步后刷新行情相关查询与同步状态
      qc.invalidateQueries({ queryKey: ["sync-settings"] });
      qc.invalidateQueries({ queryKey: ["synced-stocks"] });
      qc.invalidateQueries({ queryKey: ["holdings"] });
      qc.invalidateQueries({ queryKey: ["summary"] });
      qc.invalidateQueries({ queryKey: ["watchlist"] });
    },
  });
}

/** 本地已拉取的股票列表（含行情区间与最新更新日期）。enabled 控制按需加载（弹窗打开时）。 */
export function useSyncedStocks(enabled = true) {
  return useQuery({
    queryKey: ["synced-stocks"],
    queryFn: async () => (await api.get<SyncedStock[]>("/admin/synced-stocks")).data,
    enabled,
  });
}

export interface Diagnostics {
  app: string;
  db_path: string;
  db_size_bytes: number;
  scheduler_running: boolean;
  counts: Record<string, number>;
  last_sync_at: string | null;
  generated_at: string;
}

/** 触发浏览器下载（桌面端 webview 同样有效）。 */
function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** 导出整库为 .db.gz 并触发下载（不走 JSON api 封装，直接取二进制）。 */
export async function exportData(): Promise<void> {
  const resp = await fetch(`${getApiBase()}/api/v1/admin/data/export`);
  if (!resp.ok) throw new Error(`导出失败 (HTTP ${resp.status})`);
  const blob = await resp.blob();
  const cd = resp.headers.get("Content-Disposition") || "";
  const m = cd.match(/filename="?([^"]+)"?/);
  const filename = m ? m[1] : `hindsight_backup_${Date.now()}.db.gz`;
  triggerDownload(blob, filename);
}

/** 上传备份文件覆盖导入。 */
export async function importData(file: File): Promise<{ tables: string[] }> {
  const fd = new FormData();
  fd.append("file", file);
  const resp = await fetch(`${getApiBase()}/api/v1/admin/data/import`, {
    method: "POST",
    body: fd,
  });
  const body = await resp.json();
  if (!resp.ok || body.code !== 0) {
    throw new Error(body.message || `导入失败 (HTTP ${resp.status})`);
  }
  return body.data;
}

/** 导出诊断信息为文件：后端诊断 JSON + 桌面端日志（若可用）。 */
export async function exportDiagnostics(): Promise<void> {
  const data = (await api.get<Diagnostics>("/admin/diagnostics")).data;

  // 桌面端：附带 desktop.log（含前后端 stdout）
  let log = "";
  const diagBridge = (window as unknown as {
    tradeaiDiag?: { readLog: () => Promise<{ ok: boolean; content?: string }> };
  }).tradeaiDiag;
  if (diagBridge) {
    try {
      const res = await diagBridge.readLog();
      if (res.ok && res.content) log = res.content;
    } catch {
      /* 读日志失败不阻断诊断导出 */
    }
  }

  const text =
    `# Hindsight 诊断信息\n生成时间: ${new Date().toISOString()}\n\n` +
    `## 系统状态\n${JSON.stringify(data, null, 2)}\n\n` +
    (log ? `## 运行日志 (最近)\n${log}\n` : "");

  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  triggerDownload(blob, `hindsight_diagnostics_${Date.now()}.txt`);
}
