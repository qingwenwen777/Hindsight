"use client";

import { Bell, Moon, Search, Sun } from "lucide-react";

import { useUiStore, type BaseCurrency } from "@/lib/store/ui-store";

const CURRENCIES: BaseCurrency[] = ["JPY", "USD", "CNY"];

export function Topbar() {
  const theme = useUiStore((s) => s.theme);
  const toggleTheme = useUiStore((s) => s.toggleTheme);
  const baseCurrency = useUiStore((s) => s.baseCurrency);
  const setBaseCurrency = useUiStore((s) => s.setBaseCurrency);

  return (
    <header className="flex h-14 shrink-0 items-center gap-4 border-b border-border-subtle bg-surface px-4">
      {/* 全局搜索（/ 聚焦，后续接命令面板） */}
      <div className="flex flex-1 items-center gap-2 text-secondary">
        <div className="flex w-full max-w-md items-center gap-2 rounded-md border border-border-subtle bg-base px-3 py-1.5">
          <Search className="h-4 w-4" />
          <input
            placeholder="搜索股票…（按 / 聚焦）"
            className="w-full bg-transparent text-small text-primary outline-none placeholder:text-muted"
          />
        </div>
      </div>

      {/* 基准币种切换 */}
      <select
        value={baseCurrency}
        onChange={(e) => setBaseCurrency(e.target.value as BaseCurrency)}
        className="rounded-md border border-border-subtle bg-base px-2 py-1 text-small text-primary outline-none"
        aria-label="基准币种"
      >
        {CURRENCIES.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>

      {/* 主题切换 */}
      <button
        onClick={toggleTheme}
        className="rounded-md p-2 text-secondary hover:bg-elevated hover:text-primary"
        aria-label="切换主题"
      >
        {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      </button>

      {/* 复盘提醒铃铛 */}
      <button
        className="relative rounded-md p-2 text-secondary hover:bg-elevated hover:text-primary"
        aria-label="复盘提醒"
      >
        <Bell className="h-4 w-4" />
      </button>
    </header>
  );
}
