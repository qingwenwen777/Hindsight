"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

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
