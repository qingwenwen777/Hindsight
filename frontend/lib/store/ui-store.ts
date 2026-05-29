"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

/** 主题：深 / 浅 */
export type Theme = "dark" | "light";
/** 涨跌色方案：asia=红涨绿跌 / western=绿涨红跌 */
export type ColorScheme = "asia" | "western";
/** 基准展示币种 */
export type BaseCurrency = "JPY" | "USD" | "CNY";

interface UiState {
  theme: Theme;
  colorScheme: ColorScheme;
  baseCurrency: BaseCurrency;
  sidebarCollapsed: boolean;
  setTheme: (t: Theme) => void;
  toggleTheme: () => void;
  setColorScheme: (c: ColorScheme) => void;
  setBaseCurrency: (c: BaseCurrency) => void;
  setSidebarCollapsed: (v: boolean) => void;
}

/**
 * 全局 UI 客户端状态（持久化到 localStorage）。
 * 主题、涨跌色、基准币种、侧栏折叠等偏好。
 */
export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      theme: "dark",
      colorScheme: "western",
      baseCurrency: "JPY",
      sidebarCollapsed: true,
      setTheme: (theme) => set({ theme }),
      toggleTheme: () => set((s) => ({ theme: s.theme === "dark" ? "light" : "dark" })),
      setColorScheme: (colorScheme) => set({ colorScheme }),
      setBaseCurrency: (baseCurrency) => set({ baseCurrency }),
      setSidebarCollapsed: (sidebarCollapsed) => set({ sidebarCollapsed }),
    }),
    { name: "tradeai-ui" },
  ),
);
