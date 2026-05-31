"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { LOCALES } from "@/lib/i18n/messages";
import { useT } from "@/lib/i18n/use-t";
import { useUiStore } from "@/lib/store/ui-store";
import { useSyncAll, useSyncSettings, useUpdateSyncSettings } from "@/lib/hooks/use-sync";
import { cn } from "@/lib/utils";

export default function SettingsPage() {
  const { t, locale } = useT();
  const {
    theme,
    colorScheme,
    baseCurrency,
    setTheme,
    setColorScheme,
    setBaseCurrency,
    setLocale,
  } = useUiStore();

  const { data: sync } = useSyncSettings();
  const updateSync = useUpdateSyncSettings();
  const syncAll = useSyncAll();
  const [syncMsg, setSyncMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const runSyncNow = () => {
    setSyncMsg(null);
    syncAll.mutate(undefined, {
      onSuccess: (r) => {
        const base = t("settings.syncDone", {
          stocks: r.stocks,
          inserted: r.inserted,
          updated: r.updated,
        });
        const text =
          r.failed.length > 0
            ? `${base} · ${t("settings.syncPartial", { failed: r.failed.length })}`
            : base;
        setSyncMsg({ ok: r.failed.length === 0, text });
      },
      onError: (e) => setSyncMsg({ ok: false, text: t("settings.syncFailed", { message: (e as Error).message }) }),
    });
  };

  const lastSyncText = sync?.last_sync_at
    ? new Date(sync.last_sync_at).toLocaleString(locale === "zh" ? "zh-CN" : locale === "ja" ? "ja-JP" : "en-US")
    : t("settings.lastSyncNever");

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-h1 text-primary">{t("settings.title")}</h1>
        <p className="text-small text-secondary">{t("settings.subtitle")}</p>
      </div>

      <section>
        <h2 className="border-b border-border-default pb-2 text-title font-medium text-primary">
          {t("settings.appearance")}
        </h2>
        <div className="space-y-4 pt-4">
          <Row label={t("settings.language")}>
            {LOCALES.map((l) => (
              <Button
                key={l.value}
                size="sm"
                variant={locale === l.value ? "default" : "outline"}
                onClick={() => setLocale(l.value)}
              >
                {l.label}
              </Button>
            ))}
          </Row>
          <Row label={t("settings.theme")}>
            <Button size="sm" variant={theme === "dark" ? "default" : "outline"} onClick={() => setTheme("dark")}>
              {t("settings.dark")}
            </Button>
            <Button size="sm" variant={theme === "light" ? "default" : "outline"} onClick={() => setTheme("light")}>
              {t("settings.light")}
            </Button>
          </Row>
          <Row label={t("settings.colorScheme")}>
            <Button size="sm" variant={colorScheme === "western" ? "default" : "outline"} onClick={() => setColorScheme("western")}>
              {t("settings.western")}
            </Button>
            <Button size="sm" variant={colorScheme === "asia" ? "default" : "outline"} onClick={() => setColorScheme("asia")}>
              {t("settings.asia")}
            </Button>
          </Row>
          <Row label={t("settings.baseCurrency")}>
            {(["JPY", "USD", "CNY"] as const).map((c) => (
              <Button key={c} size="sm" variant={baseCurrency === c ? "default" : "outline"} onClick={() => setBaseCurrency(c)}>
                {c}
              </Button>
            ))}
          </Row>
        </div>
      </section>

      {/* 行情同步 */}
      <section>
        <h2 className="border-b border-border-default pb-2 text-title font-medium text-primary">
          {t("settings.marketSync")}
        </h2>
        <div className="space-y-4 pt-4">
          {/* 每日自动更新开关 */}
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="text-body font-medium text-primary">{t("settings.autoSync")}</div>
              <p className="mt-0.5 text-meta text-tertiary">{t("settings.autoSyncDesc")}</p>
              {sync && !sync.scheduler_running && (
                <p className="mt-1 text-caption text-warn">{t("settings.schedulerOff")}</p>
              )}
            </div>
            <button
              role="switch"
              aria-checked={sync?.auto_sync_enabled ?? false}
              aria-label={t("settings.autoSync")}
              disabled={!sync || updateSync.isPending}
              onClick={() => updateSync.mutate(!sync?.auto_sync_enabled)}
              className={cn(
                "relative mt-1 inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors duration-150 disabled:opacity-50",
                sync?.auto_sync_enabled ? "bg-accent" : "bg-border-strong",
              )}
            >
              <span
                className={cn(
                  "inline-block h-5 w-5 rounded-full bg-white shadow-sm transition-transform duration-150",
                  sync?.auto_sync_enabled ? "translate-x-[22px]" : "translate-x-0.5",
                )}
              />
            </button>
          </div>

          {/* 一键更新 + 上次更新时间 */}
          <div className="flex items-center justify-between gap-4 border-t border-border-subtle pt-4">
            <div className="min-w-0">
              <div className="text-meta text-tertiary">
                {t("settings.lastSync")}：<span className="tnum text-secondary">{lastSyncText}</span>
              </div>
              {syncMsg && (
                <p className={cn("mt-1 text-caption", syncMsg.ok ? "text-up" : "text-down")}>
                  {syncMsg.text}
                </p>
              )}
            </div>
            <Button
              variant="secondary"
              disabled={syncAll.isPending}
              onClick={runSyncNow}
            >
              {syncAll.isPending ? t("settings.syncing") : t("settings.syncNow")}
            </Button>
          </div>
        </div>
      </section>

      <section>
        <h2 className="border-b border-border-default pb-2 text-title font-medium text-primary">
          {t("settings.aiBackup")}
        </h2>
        <div className="space-y-2 pt-4 text-small text-secondary">
          <p>{t("settings.aiBackupDesc1")}</p>
          <p>{t("settings.aiBackupDesc2")}</p>
        </div>
      </section>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="shrink-0 text-small text-secondary">{label}</span>
      <div className="flex flex-wrap justify-end gap-2">{children}</div>
    </div>
  );
}
