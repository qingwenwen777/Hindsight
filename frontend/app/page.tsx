"use client";

import Link from "next/link";

import { PnL } from "@/components/stats/pnl";
import { Stat } from "@/components/stats/stat";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useHoldings, useSummary } from "@/lib/hooks/use-portfolio";
import { useUiStore } from "@/lib/store/ui-store";
import { formatMoney, formatQuantity, pnlDirection } from "@/lib/format";

/**
 * 仪表盘首页（接真实 API）。
 * 顶部 4 个 Stat 卡片 + Top 持仓列表。
 */
export default function DashboardPage() {
  const baseCurrency = useUiStore((s) => s.baseCurrency);
  const { data: summary, isLoading: summaryLoading } = useSummary();
  const { data: holdings, isLoading: holdingsLoading } = useHoldings();

  const topHoldings = (holdings ?? [])
    .slice()
    .sort((a, b) => Number(b.market_value ?? b.cost_basis) - Number(a.market_value ?? a.cost_basis))
    .slice(0, 5);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-h1 text-primary">仪表盘</h1>
          <p className="text-small text-secondary">记录、分析与复盘你的投资决策。</p>
        </div>
        <Link
          href="/transactions/new"
          className="rounded-md bg-accent px-4 py-2 text-small font-medium text-accent-foreground hover:bg-accent/90"
        >
          录入交易
        </Link>
      </div>

      {/* Stat 卡片 */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="总市值"
          value={
            summaryLoading
              ? "…"
              : summary?.total_market_value
                ? formatMoney(summary.total_market_value, baseCurrency)
                : "—"
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
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* 净值曲线占位（Phase 3） */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>净值 vs 基准</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex h-64 items-center justify-center rounded-md border border-dashed border-border-subtle text-secondary">
              曲线将在 Phase 3 接入 lightweight-charts
            </div>
          </CardContent>
        </Card>

        {/* Top 持仓 */}
        <Card>
          <CardHeader>
            <CardTitle>Top 持仓</CardTitle>
          </CardHeader>
          <CardContent>
            {holdingsLoading ? (
              <div className="space-y-2">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="h-12 animate-pulse rounded-md bg-elevated" />
                ))}
              </div>
            ) : topHoldings.length === 0 ? (
              <div className="py-8 text-center text-small text-secondary">
                还没有持仓，
                <Link href="/transactions/new" className="text-accent hover:underline">
                  去录入一笔交易
                </Link>
              </div>
            ) : (
              <div className="space-y-1">
                {topHoldings.map((h) => (
                  <Link
                    key={h.stock_id}
                    href={`/stocks/${h.stock_id}`}
                    className="flex items-center justify-between rounded-md px-2 py-2 hover:bg-elevated"
                  >
                    <div>
                      <div className="text-small text-primary">{h.name}</div>
                      <div className="tnum text-caption text-secondary">
                        {h.symbol} · {formatQuantity(h.shares)} 股
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="tnum text-small text-primary">
                        {formatMoney(h.market_value ?? h.cost_basis, h.currency)}
                      </div>
                      <div className="text-caption">
                        <PnL value={h.unrealized_pnl} currency={h.currency} />
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
