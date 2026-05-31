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

import { AnimatedNumber } from "@/components/stats/animated-number";
import { PnL } from "@/components/stats/pnl";
import { Button } from "@/components/ui/button";
import { FadeIn, staggerDelay } from "@/components/ui/fade-in";
import { RefetchIndicator } from "@/components/ui/refetch-indicator";
import { Skeleton } from "@/components/ui/skeleton";
import { useEquityCurve } from "@/lib/hooks/use-analytics";
import { useHoldings, useSummary } from "@/lib/hooks/use-portfolio";
import { useReviewReminders } from "@/lib/hooks/use-reminders";
import { useT } from "@/lib/i18n/use-t";
import { useUiStore } from "@/lib/store/ui-store";
import { cn } from "@/lib/utils";
import { formatMoney, pnlDirection } from "@/lib/format";

type Dir = "up" | "down" | "flat";

const dirColor = (d: Dir) =>
  d === "up" ? "text-up" : d === "down" ? "text-down" : "text-primary";

/** 主指标：大号等宽数字 + 大写标签，占据视觉重心。 */
function HeroStat({
  label,
  numeric,
  format,
  direction = "flat",
  loading,
}: {
  label: string;
  numeric: number;
  format: (n: number) => string;
  direction?: Dir;
  loading?: boolean;
}) {
  return (
    <div className="px-0 py-4 lg:px-6 lg:first:pl-0">
      <div className="label-caps">{label}</div>
      {loading ? (
        <Skeleton className="mt-2 h-8 w-32" />
      ) : (
        <AnimatedNumber
          value={numeric}
          format={format}
          className={cn("tnum mt-1.5 block text-[28px] font-medium leading-none", dirColor(direction))}
        />
      )}
    </div>
  );
}

/** 次指标：小号数字，收缩，不与主指标抢视觉。 */
function MiniStat({
  label,
  value,
  direction = "flat",
  loading,
}: {
  label: string;
  value: string;
  direction?: Dir;
  loading?: boolean;
}) {
  return (
    <div className="px-0 py-4 lg:px-6">
      <div className="label-caps">{label}</div>
      {loading ? (
        <Skeleton className="mt-2 h-6 w-24" />
      ) : (
        <div className={cn("tnum mt-2 text-mono-lg font-medium", dirColor(direction))}>{value}</div>
      )}
    </div>
  );
}

/**
 * 仪表盘首页（Hindsight / TradingView 风格）。
 * KPI 卡片 + 净值曲线 + 需要注意 + 持仓表。
 */
export default function DashboardPage() {
  const { t } = useT();
  const baseCurrency = useUiStore((s) => s.baseCurrency);
  const { data: summary, isLoading: summaryLoading, isFetching: summaryFetching } = useSummary(baseCurrency);
  const { data: holdings, isLoading: holdingsLoading, isFetching: holdingsFetching } = useHoldings();
  const { data: reminders } = useReviewReminders();
  const { data: equity } = useEquityCurve();

  // 后台刷新（有旧数据但在重新拉取）时只在顶部显示极淡指示，不退回骨架
  const refetching =
    (summaryFetching && !summaryLoading) || (holdingsFetching && !holdingsLoading);

  const moneyFmt = (n: number) => formatMoney(n, baseCurrency);
  const moneyFmtSigned = (n: number) => formatMoney(n, baseCurrency, { sign: true });

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
    <div>
      <RefetchIndicator active={refetching} />
      {/* 页头 */}
      <div className="flex items-end justify-between pb-5">
        <div>
          <h1 className="text-display text-primary">{t("dashboard.title")}</h1>
          <div className="mt-1.5 text-meta text-tertiary">
            {t("dashboard.subtitle", { currency: baseCurrency })}
          </div>
        </div>
        <Link href="/transactions/new">
          <Button>{t("dashboard.recordTrade")}</Button>
        </Link>
      </div>

      {/* KPI 带：不用卡片，一条分隔线划分的数据条。
       * 总资产 + 未实现盈亏为主（更大更重），成本/已实现为次（缩小）。 */}
      <section className="grid grid-cols-2 border-y border-border-default lg:grid-cols-4 lg:divide-x lg:divide-border-subtle">
        <HeroStat
          label={t("dashboard.totalAssets")}
          loading={summaryLoading}
          numeric={Number(summary?.total_market_value ?? summary?.total_cost ?? 0)}
          format={moneyFmt}
        />
        <HeroStat
          label={t("dashboard.unrealizedPnl")}
          loading={summaryLoading}
          numeric={Number(summary?.total_unrealized_pnl ?? 0)}
          format={moneyFmtSigned}
          direction={pnlDirection(summary?.total_unrealized_pnl)}
        />
        <MiniStat
          label={t("dashboard.totalCost")}
          loading={summaryLoading}
          value={moneyFmt(Number(summary?.total_cost ?? 0))}
        />
        <MiniStat
          label={t("dashboard.realizedPnl")}
          loading={summaryLoading}
          value={moneyFmtSigned(Number(summary?.total_realized_pnl ?? 0))}
          direction={pnlDirection(summary?.total_realized_pnl)}
        />
      </section>

      {/* 净值曲线 + 需要注意：净值占主(8列)、注意占次(4列)，靠竖分隔线分区，不堆卡片 */}
      <section className="grid grid-cols-1 gap-x-8 border-b border-border-default lg:grid-cols-12">
        <div className="py-5 lg:col-span-8 lg:border-r lg:border-border-subtle lg:pr-8">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-title font-medium text-primary">{t("dashboard.equityVsBenchmark")}</h2>
            <span className="inline-flex items-center gap-1.5 text-meta text-tertiary">
              <i className="h-[7px] w-[7px] rounded-full bg-up" />
              {t("dashboard.portfolio")}
            </span>
          </div>
          {equityData.length < 2 ? (
            <div className="flex h-[300px] items-center justify-center rounded-md border border-dashed border-border-default text-tertiary">
              {t("dashboard.equityEmpty")}
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={equityData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
                <XAxis dataKey="date" tick={{ fill: "var(--text-tertiary)", fontSize: 11 }} minTickGap={48} axisLine={{ stroke: "var(--border-default)" }} tickLine={false} />
                <YAxis tick={{ fill: "var(--text-tertiary)", fontSize: 11 }} domain={["auto", "auto"]} width={48} axisLine={false} tickLine={false} />
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
        </div>

        <div className="py-5 lg:col-span-4">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-title font-medium text-primary">{t("dashboard.attention")}</h2>
            <span className="tnum text-meta text-tertiary">
              {concentrationAlerts.length + (reminders?.length ?? 0)}
            </span>
          </div>
          <div className="grid gap-2">
            {concentrationAlerts.length === 0 && (reminders?.length ?? 0) === 0 ? (
              <div className="py-2">
                <div className="text-body font-medium text-primary">{t("dashboard.healthy")}</div>
                <div className="mt-1 text-meta text-tertiary">{t("dashboard.healthyDesc")}</div>
              </div>
            ) : (
              <>
                {concentrationAlerts.map((h) => {
                  const w = (Number(h.market_value ?? h.cost_basis) / totalWeightBase) * 100;
                  return (
                    <div
                      key={h.stock_id}
                      className="border-l-2 border-warn/70 pl-3"
                    >
                      <div className="text-body font-medium text-primary">
                        {t("dashboard.concentrationPct", { symbol: h.symbol, pct: w.toFixed(1) })}
                      </div>
                      <div className="mt-0.5 text-meta text-tertiary">
                        {t("dashboard.concentrationDesc")}
                      </div>
                    </div>
                  );
                })}
                {(reminders ?? []).slice(0, 4).map((r) => (
                  <Link
                    key={r.journal_id}
                    href={`/journals/${r.journal_id}`}
                    className="block border-l-2 border-border-strong pl-3 transition-colors hover:border-accent"
                  >
                    <div className="text-body font-medium text-primary">
                      {t("dashboard.reviewDue", {
                        name: r.name,
                        symbol: r.symbol,
                        days: r.due_milestone,
                      })}
                    </div>
                    <div className="mt-0.5 text-meta text-tertiary">
                      {t("dashboard.reviewDueDesc", { days: r.days_since })}
                    </div>
                  </Link>
                ))}
              </>
            )}
          </div>
        </div>
      </section>

      {/* 持仓表：齐平铺在画布上，紧凑行高，等宽数字右对齐，靠行分隔线区分 */}
      <section className="pt-5">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-title font-medium text-primary">{t("nav.holdings")}</h2>
          {sorted.length > 0 && (
            <span className="tnum text-meta text-tertiary">{sorted.length}</span>
          )}
        </div>
        <div className="grid h-8 grid-cols-[1.5fr_repeat(4,1fr)_0.9fr] items-center gap-4 border-b border-border-default label-caps">
          <div>{t("dashboard.col.code")}</div>
          <div className="text-right">{t("dashboard.col.price")}</div>
          <div className="text-right">{t("dashboard.col.cost")}</div>
          <div className="text-right">{t("dashboard.col.pl")}</div>
          <div className="text-right">{t("dashboard.col.weight")}</div>
          <div className="text-right">{t("dashboard.col.status")}</div>
        </div>
        {holdingsLoading ? (
          [0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className="grid h-[38px] grid-cols-[1.5fr_repeat(4,1fr)_0.9fr] items-center gap-4 border-b border-border-subtle px-0"
            >
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-16 justify-self-end" />
              <Skeleton className="h-4 w-16 justify-self-end" />
              <Skeleton className="h-4 w-14 justify-self-end" />
              <Skeleton className="h-4 w-12 justify-self-end" />
              <Skeleton className="h-4 w-14 justify-self-end" />
            </div>
          ))
        ) : sorted.length === 0 ? (
          <div className="py-12 text-center text-tertiary">
            {t("dashboard.noHoldings")}
            <Link href="/transactions/new" className="text-primary underline underline-offset-2 hover:text-secondary">
              {t("dashboard.goRecord")}
            </Link>
          </div>
        ) : (
          sorted.map((h, i) => {
            const w = totalWeightBase > 0
              ? (Number(h.market_value ?? h.cost_basis) / totalWeightBase) * 100
              : 0;
            const over = w > 20;
            const plPct =
              Number(h.cost_basis) > 0 && h.unrealized_pnl != null
                ? (Number(h.unrealized_pnl) / Number(h.cost_basis)) * 100
                : null;
            return (
              <FadeIn
                as={Link}
                key={h.stock_id}
                delay={staggerDelay(i)}
                href={`/stocks/${h.stock_id}`}
                className="grid h-[38px] grid-cols-[1.5fr_repeat(4,1fr)_0.9fr] items-center gap-4 border-b border-border-subtle transition-colors duration-150 last:border-b-0 hover:bg-elevated/50"
              >
                <div className="flex min-w-0 items-baseline gap-2">
                  <span className="tnum truncate font-medium text-primary">{h.symbol}</span>
                  <span className="truncate text-caption text-tertiary">{h.name}</span>
                </div>
                <div className="tnum text-right text-secondary">{formatMoney(h.last_price ?? h.avg_cost, h.currency)}</div>
                <div className="tnum text-right text-tertiary">{formatMoney(h.avg_cost, h.currency)}</div>
                <div className="text-right">
                  {plPct != null ? <PnL value={plPct} mode="percent" /> : <span className="text-tertiary">—</span>}
                </div>
                <div className="tnum text-right text-secondary">{w.toFixed(1)}%</div>
                <div className="text-right">
                  {over ? (
                    <span className="text-meta font-medium text-down">{t("dashboard.concentrationBadge")}</span>
                  ) : (
                    <span className="text-meta text-tertiary">{t("dashboard.hold")}</span>
                  )}
                </div>
              </FadeIn>
            );
          })
        )}
      </section>
    </div>
  );
}
