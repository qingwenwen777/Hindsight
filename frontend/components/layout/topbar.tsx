"use client";

import { Bell, Moon, Search, Settings, Sun } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";

import { LanguageSwitcher } from "@/components/layout/language-switcher";
import { useReviewReminders } from "@/lib/hooks/use-reminders";
import { useT } from "@/lib/i18n/use-t";
import { useUiStore, type BaseCurrency } from "@/lib/store/ui-store";

const CURRENCIES: BaseCurrency[] = ["JPY", "USD", "CNY"];

export function Topbar() {
  const router = useRouter();
  const { t } = useT();
  const theme = useUiStore((s) => s.theme);
  const toggleTheme = useUiStore((s) => s.toggleTheme);
  const baseCurrency = useUiStore((s) => s.baseCurrency);
  const setBaseCurrency = useUiStore((s) => s.setBaseCurrency);
  const { data: reminders } = useReviewReminders();
  const unread = reminders?.length ?? 0;
  const searchRef = useRef<HTMLInputElement>(null);

  // 按 "/" 聚焦搜索（输入框内除外）
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (e.key === "/" && tag !== "INPUT" && tag !== "TEXTAREA") {
        e.preventDefault();
        searchRef.current?.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const cycleCurrency = () => {
    const idx = CURRENCIES.indexOf(baseCurrency);
    setBaseCurrency(CURRENCIES[(idx + 1) % CURRENCIES.length]);
  };

  return (
    <header className="flex h-[60px] shrink-0 items-center gap-5 border-b border-border-subtle bg-surface px-6 card-shadow">
      {/* 全局搜索（pill 样式，点击/聚焦后回车进关注页；Cmd+K 开命令面板） */}
      <div className="flex h-10 min-w-[260px] max-w-[520px] flex-1 items-center gap-2.5 rounded-pill bg-elevated px-4 text-tertiary">
        <Search className="h-4 w-4" />
        <input
          ref={searchRef}
          placeholder={t("topbar.searchPlaceholder")}
          className="w-full bg-transparent text-body text-primary outline-none placeholder:text-tertiary"
          onKeyDown={(e) => {
            if (e.key === "Enter" && e.currentTarget.value.trim()) {
              router.push(`/watchlist`);
            }
          }}
        />
        <kbd className="hidden rounded border border-border-default px-1.5 py-0.5 text-caption text-tertiary sm:inline">
          ⌘K
        </kbd>
      </div>

      <div className="flex items-center gap-2">
        {/* 语言切换 */}
        <LanguageSwitcher />

        {/* 基准币种切换 */}
        <button
          onClick={cycleCurrency}
          className="tnum flex h-[34px] items-center rounded-md border border-border-default px-3 text-body font-medium text-secondary hover:border-border-strong"
          aria-label={t("topbar.baseCurrency")}
        >
          {baseCurrency}
        </button>

        {/* 主题切换 */}
        <button
          onClick={toggleTheme}
          className="flex h-[34px] w-[34px] items-center justify-center rounded-md border border-border-default text-secondary hover:bg-elevated hover:text-primary"
          aria-label={t("topbar.toggleTheme")}
        >
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>

        {/* 复盘提醒 */}
        <button
          onClick={() => router.push("/journals")}
          className="relative flex h-[34px] w-[34px] items-center justify-center rounded-md border border-border-default text-secondary hover:bg-elevated hover:text-primary"
          aria-label={t("topbar.reminders")}
        >
          <Bell className="h-4 w-4" />
          {unread > 0 && (
            <span className="tnum absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-medium text-white">
              {unread > 99 ? "99+" : unread}
            </span>
          )}
        </button>

        {/* 设置 */}
        <button
          onClick={() => router.push("/settings")}
          className="flex h-[34px] w-[34px] items-center justify-center rounded-md border border-border-default text-secondary hover:bg-elevated hover:text-primary"
          aria-label={t("topbar.settings")}
        >
          <Settings className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}
