"use client";

import Link from "next/link";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { PnL } from "@/components/stats/pnl";
import { Stat } from "@/components/stats/stat";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useEquityCurve } from "@/lib/hooks/use-analytics";
import { useHoldings, useSummary } from "@/lib/hooks/use-portfolio";
import { useReviewReminders } from "@/lib/hooks/use-reminders";
import { useT } from "@/lib/i18n/use-t";
import { useUiStore } from "@/lib/store/ui-store";
import { formatMoney, formatPercent, pnlDirection } from "@/lib/format";

/**
 * 仪表盘首页（Hindsight / TradingView 风格）。
 * KPI 卡片 + 净值曲线 + 需要注意 + 持仓表。
 */
export default function DashboardPage() {
  const { t } = useT();
  const baseCurrency = useUiStore((s) => s.baseCurrency);
  const { data: summary, isLoading: summaryLoading } = useSummary(baseCurrency);
  const { data: holdings, isLoading: holdingsLoading } = useHoldings();
  const { data: reminders } = useReviewReminders();
  const { data: equity } = useEquityCurve();

  const equityData =
    equity?.dates.map((d, i) => ({ date: d, value: equity.normalized[i] })) ?? [];

  const totalWeightBase = (holdings ?? []).reduce(
    (acc, h) => acc + Number(h.market_value ?? h.cost_basis ?? 0),
    0,
  );
  const sorted = (holdings ?? [])
    .slice()
    .sort(
      (a, b) =>
        Number(b.market_value ?? b.cost_basis) - Number(a.market_value ?? a.cost_basis),
    );

  // 集中度告警（单股 > 20%）
  const concentrationAlerts = sorted.filter(
    (h) => totalWeightBase > 0 && Number(h.market_value ?? h.cost_basis) / totalWeightBase > 0.2,
  );

  return (
    <div className="space-y-4">
      {/* 页头 */}
      <div className="mb-4.5 flex items-end justify-between">
        <div>
          <h1 className="text-display text-secondary">{t("dashboard.title")}</h1>
          <div className="mt-2 text-meta text-tertiary">
            {t("dashboard.subtitle", { currency: baseCurrency })}
          </div>
        </div>
        <Link href="/transactions/new">
          <Button>{t("dashboard.recordTrade")}</Button>
        </Link>
      </div>

      {/* KPI 网格 */}
      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Stat
          label={t("dashboard.totalAssets")}
          value={
            summaryLoading
              ? "…"
              : summary?.total_market_value
                ? formatMoney(summary.total_market_value, baseCurrency)
                : formatMoney(summary?.total_cost, baseCurrency)
          }
        />
        <Stat
          label={t("dashboard.totalCost")}
          value={summaryLoading ? "…" : formatMoney(summary?.total_cost, baseCurrency)}
        />
        <Stat
          label={t("dashboard.unrealizedPnl")}
          value={
            summaryLoading
              ? "…"
              : formatMoney(summary?.total_unrealized_pnl, baseCurrency, { sign: true })
          }
          colorValue
          direction={pnlDirection(summary?.total_unrealized_pnl)}
        />
        <Stat
          label={t("dashboard.realizedPnl")}
          value={
            summaryLoading
              ? "…"
              : formatMoney(summary?.total_realized_pnl, baseCurrency, { sign: true })
          }
          colorValue
          direction={pnlDirection(summary?.total_realized_pnl)}
        />
      </section>

      {/* 12 列：净值曲线 + 需要注意 */}
      <section className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <Card className="p-5 lg:col-span-8">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-title font-medium text-primary">{t("dashboard.equityVsBenchmark")}</h2>
            <div className="flex gap-3.5 text-meta text-tertiary">
              <span className="inline-flex items-center gap-1.5">
                <i className="h-[7px] w-[7px] rounded-full bg-up" />{t("dashboard.portfolio")}
              </span>
            </div>
          </div>
          {equityData.length < 2 ? (
            <div className="flex h-[300px] items-center justify-center rounded-md border border-dashed border-border-default text-tertiary">
              {t("dashboard.equityEmpty")}
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={equityData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-default)" />
                <XAxis dataKey="date" tick={{ fill: "var(--text-tertiary)", fontSize: 11 }} minTickGap={48} />
                <YAxis tick={{ fill: "var(--text-tertiary)", fontSize: 11 }} domain={["auto", "auto"]} width={48} />
                <Tooltip
                  contentStyle={{
                    background: "var(--bg-elevated)",
                    border: "1px solid var(--border-default)",
                    borderRadius: 8,
                    color: "var(--text-primary)",
                    fontSize: 12,
                  }}
                />
                <Line type="monotone" dataKey="value" stroke="var(--up)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </Card>

        <Card className="p-5 lg:col-span-4">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-title font-medium text-primary">{t("dashboard.attention")}</h2>
            <span className="rounded-badge border border-border-default bg-elevated px-1.5 py-0.5 text-badge font-medium text-secondary">
              {concentrationAlerts.length + (reminders?.length ?? 0)} {t("dashboard.alerts")}
            </span>
          </div>
          <div className="grid gap-3">
            {concentrationAlerts.length === 0 && (reminders?.length ?? 0) === 0 ? (
              <div className="rounded-md border border-border-default bg-base p-3.5">
                <div className="text-body font-medium text-primary">{t("dashboard.healthy")}</div>
                <div className="mt-1.5 text-meta text-tertiary">{t("dashboard.healthyDesc")}</div>
              </div>
            ) : (
              <>
                {concentrationAlerts.map((h) => {
                  const w = (Number(h.market_value ?? h.cost_basis) / totalWeightBase) * 100;
                  return (
                    <div
                      key={h.stock_id}
                      className="rounded-md border border-border-default bg-base p-3.5"
                    >
                      <div className="text-body font-medium text-primary">
                        {t("dashboard.concentrationPct", { symbol: h.symbol, pct: w.toFixed(1) })}
                      </div>
                      <div className="mt-1.5 text-meta text-tertiary">
                        {t("dashboard.concentrationDesc")}
                      </div>
                    </div>
                  );
                })}
                {(reminders ?? []).slice(0, 4).map((r) => (
                  <Link
                    key={r.journal_id}
                    href={`/journals/${r.journal_id}`}
                    className="block rounded-md border border-border-default bg-base p-3.5 hover:bg-elevated"
                  >
                    <div className="text-body font-medium text-primary">
                      {t("dashboard.reviewDue", {
                        name: r.name,
                        symbol: r.symbol,
                        days: r.due_milestone,
                      })}
                    </div>
                    <div className="mt-1.5 text-meta text-tertiary">
                      {t("dashboard.reviewDueDesc", { days: r.days_since })}
                    </div>
                  </Link>
                ))}
              </>
            )}
          </div>
        </Card>
      </section>

      {/* 持仓表 */}
      <Card className="overflow-hidden">
        <div className="grid min-h-[40px] grid-cols-[1.25fr_repeat(4,1fr)_1.1fr] items-center gap-4 bg-elevated px-5 label-caps">
          <div>{t("dashboard.col.code")}</div>
          <div className="text-right">{t("dashboard.col.price")}</div>
          <div className="text-right">{t("dashboard.col.cost")}</div>
          <div className="text-right">{t("dashboard.col.pl")}</div>
          <div className="text-right">{t("dashboard.col.weight")}</div>
          <div>{t("dashboard.col.status")}</div>
        </div>
        {holdingsLoading ? (
          [0, 1, 2].map((i) => (
            <div key={i} className="border-b border-border-default px-5 py-3">
              <div className="h-6 animate-pulse rounded bg-elevated" />
            </div>
          ))
        ) : sorted.length === 0 ? (
          <div className="px-5 py-12 text-center text-tertiary">
            {t("dashboard.noHoldings")}
            <Link href="/transactions/new" className="text-primary underline underline-offset-2 hover:text-secondary">
              {t("dashboard.goRecord")}
            </Link>
          </div>
        ) : (
          sorted.map((h) => {
            const w = totalWeightBase > 0
              ? (Number(h.market_value ?? h.cost_basis) / totalWeightBase) * 100
              : 0;
            const over = w > 20;
            const plPct =
              Number(h.cost_basis) > 0 && h.unrealized_pnl != null
                ? (Number(h.unrealized_pnl) / Number(h.cost_basis)) * 100
                : null;
            return (
              <Link
                key={h.stock_id}
                href={`/stocks/${h.stock_id}`}
                className="grid min-h-[44px] grid-cols-[1.25fr_repeat(4,1fr)_1.1fr] items-center gap-4 border-b border-border-default px-5 last:border-b-0 hover:bg-elevated"
              >
                <div>
                  <div className="font-medium text-primary">{h.symbol}</div>
                  <div className="mt-0.5 text-caption text-tertiary">{h.name}</div>
                </div>
                <div className="tnum text-right text-primary">{formatMoney(h.last_price ?? h.avg_cost, h.currency)}</div>
                <div className="tnum text-right text-tertiary">{formatMoney(h.avg_cost, h.currency)}</div>
                <div className="text-right">
                  {plPct != null ? <PnL value={plPct} mode="percent" /> : <span className="text-tertiary">—</span>}
                </div>
                <div className="tnum text-right text-secondary">{w.toFixed(1)}%</div>
                <div>
                  {over ? (
                    <span className="rounded-badge border border-down/55 bg-elevated px-1.5 py-0.5 text-badge font-medium text-down">
                      {t("dashboard.concentrationBadge")}
                    </span>
                  ) : (
                    <span className="rounded-badge border border-border-default bg-elevated px-1.5 py-0.5 text-badge font-medium text-secondary">
                      {t("dashboard.hold")}
                    </span>
                  )}
                </div>
              </Link>
            );
          })
        )}
      </Card>
    </div>
  );
}
