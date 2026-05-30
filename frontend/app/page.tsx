"use client";

import Link from "next/link";

import { PnL } from "@/components/stats/pnl";
import { Stat } from "@/components/stats/stat";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useHoldings, useSummary } from "@/lib/hooks/use-portfolio";
import { useReviewReminders } from "@/lib/hooks/use-reminders";
import { useUiStore } from "@/lib/store/ui-store";
import { formatMoney, formatPercent, pnlDirection } from "@/lib/format";

/**
 * 仪表盘首页（Hindsight / TradingView 风格）。
 * KPI 卡片 + 净值曲线 + 需要注意 + 持仓表。
 */
export default function DashboardPage() {
  const baseCurrency = useUiStore((s) => s.baseCurrency);
  const { data: summary, isLoading: summaryLoading } = useSummary();
  const { data: holdings, isLoading: holdingsLoading } = useHoldings();
  const { data: reminders } = useReviewReminders();

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
          <h1 className="text-display text-secondary">仪表盘</h1>
          <div className="mt-2 text-meta text-tertiary">个人组合复盘 · 基准币种 {baseCurrency}</div>
        </div>
        <Link href="/transactions/new">
          <Button>录入交易</Button>
        </Link>
      </div>

      {/* KPI 网格 */}
      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="Total Assets"
          value={
            summaryLoading
              ? "…"
              : summary?.total_market_value
                ? formatMoney(summary.total_market_value, baseCurrency)
                : formatMoney(summary?.total_cost, baseCurrency)
          }
        />
        <Stat
          label="总成本"
          value={summaryLoading ? "…" : formatMoney(summary?.total_cost, baseCurrency)}
        />
        <Stat
          label="浮动盈亏"
          value={
            summaryLoading
              ? "…"
              : formatMoney(summary?.total_unrealized_pnl, baseCurrency, { sign: true })
          }
          colorValue
          direction={pnlDirection(summary?.total_unrealized_pnl)}
        />
        <Stat
          label="已实现盈亏"
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
            <h2 className="text-title font-medium text-primary">净值 vs 基准</h2>
            <div className="flex gap-3.5 text-meta text-tertiary">
              <span className="inline-flex items-center gap-1.5">
                <i className="h-[7px] w-[7px] rounded-full bg-up" />组合
              </span>
              <span className="inline-flex items-center gap-1.5">
                <i className="h-[7px] w-[7px] rounded-full bg-accent" />基准
              </span>
            </div>
          </div>
          <div className="flex h-[300px] items-center justify-center rounded-md border border-dashed border-border-default text-tertiary">
            净值曲线将在接入历史估值快照后渲染
          </div>
        </Card>

        <Card className="p-5 lg:col-span-4">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-title font-medium text-primary">需要注意</h2>
            <span className="rounded-badge border border-border-default bg-elevated px-1.5 py-0.5 text-badge font-medium text-secondary">
              {concentrationAlerts.length + (reminders?.length ?? 0)} alerts
            </span>
          </div>
          <div className="grid gap-3">
            {concentrationAlerts.length === 0 && (reminders?.length ?? 0) === 0 ? (
              <div className="rounded-md border border-border-default border-l-2 border-l-up bg-base p-3.5">
                <div className="text-body font-medium text-primary">组合健康</div>
                <div className="mt-1.5 text-meta text-tertiary">暂无超阈值告警与到期复盘。</div>
              </div>
            ) : (
              <>
                {concentrationAlerts.map((h) => {
                  const w = (Number(h.market_value ?? h.cost_basis) / totalWeightBase) * 100;
                  return (
                    <div
                      key={h.stock_id}
                      className="rounded-md border border-border-default border-l-2 border-l-down bg-base p-3.5"
                    >
                      <div className="text-body font-medium text-primary">
                        {h.symbol} 占 <span className="tnum">{w.toFixed(1)}%</span>
                      </div>
                      <div className="mt-1.5 text-meta text-tertiary">
                        超 20% 阈值，建议复查集中度假设。
                      </div>
                    </div>
                  );
                })}
                {(reminders ?? []).slice(0, 4).map((r) => (
                  <Link
                    key={r.journal_id}
                    href={`/journals/${r.journal_id}`}
                    className="block rounded-md border border-border-default border-l-2 border-l-accent bg-base p-3.5 hover:bg-elevated"
                  >
                    <div className="text-body font-medium text-primary">
                      {r.name} <span className="tnum text-tertiary">{r.symbol}</span> 待 {r.due_milestone} 天复盘
                    </div>
                    <div className="mt-1.5 text-meta text-tertiary">
                      决策已 <span className="tnum">{r.days_since}</span> 天，去补一条复盘。
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
          <div>Code</div>
          <div className="text-right">Price</div>
          <div className="text-right">Cost</div>
          <div className="text-right">P/L</div>
          <div className="text-right">Weight</div>
          <div>Status</div>
        </div>
        {holdingsLoading ? (
          [0, 1, 2].map((i) => (
            <div key={i} className="border-b border-border-default px-5 py-3">
              <div className="h-6 animate-pulse rounded bg-elevated" />
            </div>
          ))
        ) : sorted.length === 0 ? (
          <div className="px-5 py-12 text-center text-tertiary">
            还没有持仓，
            <Link href="/transactions/new" className="text-accent hover:underline">
              去录入一笔交易
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
                      集中度告警
                    </span>
                  ) : (
                    <span className="rounded-badge border border-border-default bg-elevated px-1.5 py-0.5 text-badge font-medium text-secondary">
                      Hold
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
