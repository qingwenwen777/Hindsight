"use client";

import { useEffect } from "react";

import { useUiStore } from "@/lib/store/ui-store";

/** 语言 -> html lang 属性值 */
const LANG_ATTR: Record<string, string> = {
  zh: "zh-CN",
  ja: "ja-JP",
  en: "en",
};

/**
 * 主题、涨跌色与语言应用器。
 * 把 zustand 中的 theme / colorScheme / locale 同步到 <html> 的 class 与属性，
 * 驱动 globals.css 中的 CSS 变量切换，并让字体按语言匹配。
 */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const theme = useUiStore((s) => s.theme);
  const colorScheme = useUiStore((s) => s.colorScheme);
  const locale = useUiStore((s) => s.locale);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove("dark", "light");
    root.classList.add(theme);
    root.style.colorScheme = theme;
    root.setAttribute("data-color-scheme", colorScheme);
  }, [theme, colorScheme]);

  useEffect(() => {
    document.documentElement.setAttribute("lang", LANG_ATTR[locale] ?? "zh-CN");
  }, [locale]);

  return <>{children}</>;
}
