"use client";

import { Bell, Moon, Search, Settings, Sun } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { LanguageSwitcher } from "@/components/layout/language-switcher";
import { useReviewReminders } from "@/lib/hooks/use-reminders";
import { useMarkAlertRead, usePriceAlerts } from "@/lib/hooks/use-price-alerts";
import { useT } from "@/lib/i18n/use-t";
import { useUiStore, type BaseCurrency } from "@/lib/store/ui-store";
import { cn } from "@/lib/utils";

const CURRENCIES: BaseCurrency[] = ["JPY", "USD", "CNY"];

export function Topbar() {
  const router = useRouter();
  const { t } = useT();
  const theme = useUiStore((s) => s.theme);
  const toggleTheme = useUiStore((s) => s.toggleTheme);
  const baseCurrency = useUiStore((s) => s.baseCurrency);
  const setBaseCurrency = useUiStore((s) => s.setBaseCurrency);
  const { data: reminders } = useReviewReminders();
  const { data: alerts } = usePriceAlerts();
  const markAlertRead = useMarkAlertRead();
  const searchRef = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const bellRef = useRef<HTMLDivElement>(null);

  const unreadAlerts = (alerts ?? []).filter((a) => !a.is_read);
  const reminderCount = reminders?.length ?? 0;
  const unread = unreadAlerts.length + reminderCount;

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

  // 点击外部关闭通知
  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (bellRef.current && !bellRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const cycleCurrency = () => {
    const idx = CURRENCIES.indexOf(baseCurrency);
    setBaseCurrency(CURRENCIES[(idx + 1) % CURRENCIES.length]);
  };

  return (
    <header className="relative z-30 flex h-[60px] shrink-0 items-center gap-5 border-b border-border-subtle bg-surface px-6 card-shadow">
      {/* 全局搜索 */}
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

        {/* 通知（复盘提醒 + 价格提醒聚合） */}
        <div className="relative" ref={bellRef}>
          <button
            onClick={() => setOpen((o) => !o)}
            className="relative flex h-[34px] w-[34px] items-center justify-center rounded-md border border-border-default text-secondary hover:bg-elevated hover:text-primary"
            aria-label={t("topbar.notifications")}
          >
            <Bell className="h-4 w-4" />
            {unread > 0 && (
              <span className="tnum absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-medium text-white">
                {unread > 99 ? "99+" : unread}
              </span>
            )}
          </button>

          {open && (
            <div className="absolute right-0 top-full z-50 mt-1 max-h-[420px] w-80 overflow-y-auto rounded-md border border-border-strong bg-elevated py-1 shadow-xl">
              {unread === 0 && (
                <p className="px-3 py-6 text-center text-meta text-tertiary">{t("alerts.none")}</p>
              )}

              {/* 价格提醒 */}
              {unreadAlerts.length > 0 && (
                <div className="px-1 py-1">
                  <div className="px-2 pb-1 label-caps">{t("alerts.title")}</div>
                  {unreadAlerts.map((a) => (
                    <button
                      key={a.id}
                      onClick={() => {
                        markAlertRead.mutate(a.id);
                        setOpen(false);
                        router.push(`/stocks/${a.stock_id}`);
                      }}
                      className="flex w-full flex-col items-start gap-0.5 rounded-md px-3 py-2 text-left hover:bg-base"
                    >
                      <span className="text-body text-primary">
                        {a.name}{" "}
                        <span className="tnum text-tertiary">{a.symbol}</span>
                      </span>
                      <span className={cn("text-caption", a.alert_type === "TARGET" ? "text-up" : "text-down")}>
                        {a.alert_type === "TARGET" ? t("alerts.target") : t("alerts.stop")}
                        {" · "}
                        <span className="tnum">{t("alerts.threshold")} {a.threshold} / {t("alerts.triggered")} {a.triggered_price}</span>
                      </span>
                    </button>
                  ))}
                </div>
              )}

              {/* 复盘提醒 */}
              {reminderCount > 0 && (
                <div className="px-1 py-1">
                  <div className="px-2 pb-1 label-caps">{t("reminders.title")}</div>
                  {(reminders ?? []).slice(0, 8).map((r) => (
                    <button
                      key={r.journal_id}
                      onClick={() => {
                        setOpen(false);
                        router.push(`/journals/${r.journal_id}`);
                      }}
                      className="flex w-full flex-col items-start gap-0.5 rounded-md px-3 py-2 text-left hover:bg-base"
                    >
                      <span className="text-body text-primary">
                        {r.name} <span className="tnum text-tertiary">{r.symbol}</span>
                      </span>
                      <span className="text-caption text-tertiary">
                        {t("dashboard.reviewDue", { name: "", symbol: "", days: r.due_milestone }).trim()}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

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
