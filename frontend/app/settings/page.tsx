"use client";

import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { LOCALES } from "@/lib/i18n/messages";
import { useT } from "@/lib/i18n/use-t";
import { useUiStore } from "@/lib/store/ui-store";
import {
  exportData,
  exportDiagnostics,
  importData,
  useSyncAll,
  useSyncedStocks,
  useSyncSettings,
  useUpdateSyncSettings,
} from "@/lib/hooks/use-sync";
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

          {/* 查看本地已拉取的股票 */}
          <div className="border-t border-border-subtle pt-4">
            <SyncedStocksDialog />
          </div>
        </div>
      </section>

      {/* 数据与备份 */}
      <DataSection />

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

/** 数据与备份：导出/导入数据、导出诊断信息。 */
function DataSection() {
  const { t } = useT();
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState<"export" | "import" | "diag" | null>(null);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const onExport = async () => {
    setMsg(null);
    setBusy("export");
    try {
      await exportData();
      setMsg({ ok: true, text: t("settings.exported") });
    } catch (e) {
      setMsg({ ok: false, text: (e as Error).message });
    } finally {
      setBusy(null);
    }
  };

  const onPickImport = () => {
    if (!window.confirm(t("settings.importConfirm"))) return;
    fileRef.current?.click();
  };

  const onImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = ""; // 允许重复选同一文件
    if (!file) return;
    setMsg(null);
    setBusy("import");
    try {
      const res = await importData(file);
      setMsg({ ok: true, text: t("settings.imported", { tables: res.tables.length }) });
    } catch (err) {
      setMsg({ ok: false, text: t("settings.importFailed", { message: (err as Error).message }) });
    } finally {
      setBusy(null);
    }
  };

  const onExportDiag = async () => {
    setMsg(null);
    setBusy("diag");
    try {
      await exportDiagnostics();
      setMsg({ ok: true, text: t("settings.diagExported") });
    } catch (e) {
      setMsg({ ok: false, text: (e as Error).message });
    } finally {
      setBusy(null);
    }
  };

  return (
    <section>
      <h2 className="border-b border-border-default pb-2 text-title font-medium text-primary">
        {t("settings.dataSection")}
      </h2>
      <div className="space-y-4 pt-4">
        <DataRow
          title={t("settings.export")}
          desc={t("settings.exportDesc")}
          action={
            <Button variant="secondary" disabled={busy !== null} onClick={onExport}>
              {busy === "export" ? t("settings.exporting") : t("settings.export")}
            </Button>
          }
        />
        <DataRow
          title={t("settings.import")}
          desc={t("settings.importDesc")}
          action={
            <>
              <input
                ref={fileRef}
                type="file"
                accept=".gz,.db"
                className="hidden"
                onChange={onImport}
              />
              <Button variant="outline" disabled={busy !== null} onClick={onPickImport}>
                {busy === "import" ? t("settings.importing") : t("settings.import")}
              </Button>
            </>
          }
        />
        <DataRow
          title={t("settings.exportDiag")}
          desc={t("settings.exportDiagDesc")}
          action={
            <Button variant="outline" disabled={busy !== null} onClick={onExportDiag}>
              {t("settings.exportDiag")}
            </Button>
          }
        />
        {msg && (
          <p className={cn("text-caption", msg.ok ? "text-up" : "text-down")}>{msg.text}</p>
        )}
      </div>
    </section>
  );
}

function DataRow({
  title,
  desc,
  action,
}: {
  title: string;
  desc: string;
  action: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-border-subtle pb-4 last:border-b-0 last:pb-0">
      <div className="min-w-0">
        <div className="text-body font-medium text-primary">{title}</div>
        <p className="mt-0.5 text-meta text-tertiary">{desc}</p>
      </div>
      <div className="shrink-0">{action}</div>
    </div>
  );
}

/** 本地已拉取股票弹窗：点击按钮打开，按需加载列表。 */
function SyncedStocksDialog() {
  const { t, locale } = useT();
  const [open, setOpen] = useState(false);
  const { data: stocks, isLoading } = useSyncedStocks(open);

  const fmtDate = (d: string | null) => {
    if (!d) return t("settings.stockNotSynced");
    return new Date(d).toLocaleDateString(
      locale === "zh" ? "zh-CN" : locale === "ja" ? "ja-JP" : "en-US",
    );
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          {t("settings.viewStocks")}
        </Button>
      </DialogTrigger>
      <DialogContent
        title={t("settings.stocksTitle")}
        description={t("settings.stocksSubtitle")}
        className="max-w-xl"
      >
        <div className="max-h-[60vh] overflow-y-auto">
          {isLoading ? (
            <div className="space-y-2 py-2">
              {[0, 1, 2, 3, 4].map((i) => (
                <Skeleton key={i} className="h-9 w-full" />
              ))}
            </div>
          ) : !stocks || stocks.length === 0 ? (
            <p className="py-10 text-center text-small text-tertiary">
              {t("settings.stocksEmpty")}
            </p>
          ) : (
            <>
              <div className="pb-2 text-caption text-tertiary">
                {t("settings.stocksCount", { count: stocks.length })}
              </div>
              <table className="w-full text-small">
                <thead>
                  <tr className="border-y border-border-default label-caps">
                    <th className="px-2 py-2 text-left font-normal">{t("settings.col.stock")}</th>
                    <th className="px-2 py-2 text-right font-normal">{t("settings.col.bars")}</th>
                    <th className="px-2 py-2 text-right font-normal">{t("settings.col.lastDate")}</th>
                  </tr>
                </thead>
                <tbody>
                  {stocks.map((s) => (
                    <tr key={s.stock_id} className="border-b border-border-subtle">
                      <td className="px-2 py-2">
                        <span className="text-primary">{s.name}</span>{" "}
                        <span className="tnum text-tertiary">{s.symbol} · {s.market}</span>
                      </td>
                      <td className="tnum px-2 py-2 text-right text-secondary">
                        {s.bars > 0 ? s.bars : "—"}
                      </td>
                      <td
                        className={cn(
                          "tnum px-2 py-2 text-right",
                          s.last_date ? "text-secondary" : "text-tertiary",
                        )}
                      >
                        {fmtDate(s.last_date)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
