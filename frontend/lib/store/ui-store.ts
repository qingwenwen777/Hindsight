"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

/** 主题：深 / 浅 */
export type Theme = "dark" | "light";
/** 涨跌色方案：asia=红涨绿跌 / western=绿涨红跌 */
export type ColorScheme = "asia" | "western";
/** 基准展示币种 */
export type BaseCurrency = "JPY" | "USD" | "CNY";
/** 界面语言：中 / 日 / 英 */
export type Locale = "zh" | "ja" | "en";

interface UiState {
  theme: Theme;
  colorScheme: ColorScheme;
  baseCurrency: BaseCurrency;
  locale: Locale;
  sidebarCollapsed: boolean;
  // AI 对话默认服务商/模型（全局默认，可在对话里临时切换）
  chatProviderId: number | null;
  chatModel: string | null;
  setTheme: (t: Theme) => void;
  toggleTheme: () => void;
  setColorScheme: (c: ColorScheme) => void;
  setBaseCurrency: (c: BaseCurrency) => void;
  setLocale: (l: Locale) => void;
  setSidebarCollapsed: (v: boolean) => void;
  setChatProvider: (providerId: number | null, model: string | null) => void;
}

/**
 * 全局 UI 客户端状态（持久化到 localStorage）。
 * 主题、涨跌色、基准币种、界面语言、侧栏折叠、AI 对话默认服务商等偏好。
 */
export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      theme: "dark",
      colorScheme: "western",
      baseCurrency: "JPY",
      locale: "zh",
      sidebarCollapsed: false,
      chatProviderId: null,
      chatModel: null,
      setTheme: (theme) => set({ theme }),
      toggleTheme: () => set((s) => ({ theme: s.theme === "dark" ? "light" : "dark" })),
      setColorScheme: (colorScheme) => set({ colorScheme }),
      setBaseCurrency: (baseCurrency) => set({ baseCurrency }),
      setLocale: (locale) => set({ locale }),
      setSidebarCollapsed: (sidebarCollapsed) => set({ sidebarCollapsed }),
      setChatProvider: (chatProviderId, chatModel) => set({ chatProviderId, chatModel }),
    }),
    { name: "tradeai-ui" },
  ),
);

