"use client";

import { useEffect } from "react";

import { useUiStore } from "@/lib/store/ui-store";

/**
 * 主题与涨跌色应用器。
 * 把 zustand 中的 theme / colorScheme 同步到 <html> 的 class 与 data 属性，
 * 驱动 globals.css 中的 CSS 变量切换。
 */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const theme = useUiStore((s) => s.theme);
  const colorScheme = useUiStore((s) => s.colorScheme);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove("dark", "light");
    root.classList.add(theme);
    root.style.colorScheme = theme;
    root.setAttribute("data-color-scheme", colorScheme);
  }, [theme, colorScheme]);

  return <>{children}</>;
}
