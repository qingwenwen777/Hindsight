"use client";

import Link from "next/link";

import { PnL } from "@/components/stats/pnl";
import { Card } from "@/components/ui/card";
import { formatMoney, formatQuantity } from "@/lib/format";
import { useHoldings } from "@/lib/hooks/use-portfolio";

export default function HoldingsPage() {
  const { data: holdings, isLoading } = useHoldings();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-h1 text-primary">持仓</h1>
        <p className="text-small text-secondary">FIFO 成本口径，浮盈基于最新收盘价。</p>
      </div>

      <Card className="overflow-hidden">
        <table className="w-full text-small">
          <thead>
            <tr className="border-b border-border-subtle text-caption text-secondary">
              <th className="px-4 py-3 text-left">标的</th>
              <th className="px-4 py-3 text-right">持股</th>
              <th className="px-4 py-3 text-right">均价</th>
              <th className="px-4 py-3 text-right">现价</th>
              <th className="px-4 py-3 text-right">市值</th>
              <th className="px-4 py-3 text-right">浮动盈亏</th>
              <th className="px-4 py-3 text-right">已实现</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              [0, 1, 2].map((i) => (
                <tr key={i}>
                  <td colSpan={7} className="px-4 py-3">
                    <div className="h-6 animate-pulse rounded bg-elevated" />
                  </td>
                </tr>
              ))
            ) : !holdings || holdings.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center text-secondary">
                  暂无持仓，
                  <Link href="/transactions/new" className="text-primary underline underline-offset-2 hover:text-secondary">
                    去录入
                  </Link>
                </td>
              </tr>
            ) : (
              holdings.map((h) => (
                <tr key={h.stock_id} className="border-b border-border-subtle/50 hover:bg-elevated">
                  <td className="px-4 py-3">
                    <Link href={`/stocks/${h.stock_id}`} className="text-primary hover:text-accent">
                      {h.name} <span className="tnum text-secondary">{h.symbol}</span>
                    </Link>
                  </td>
                  <td className="tnum px-4 py-3 text-right text-primary">{formatQuantity(h.shares)}</td>
                  <td className="tnum px-4 py-3 text-right text-secondary">{formatMoney(h.avg_cost, h.currency)}</td>
                  <td className="tnum px-4 py-3 text-right text-primary">{formatMoney(h.last_price, h.currency)}</td>
                  <td className="tnum px-4 py-3 text-right text-primary">{formatMoney(h.market_value ?? h.cost_basis, h.currency)}</td>
                  <td className="px-4 py-3 text-right"><PnL value={h.unrealized_pnl} currency={h.currency} /></td>
                  <td className="px-4 py-3 text-right"><PnL value={h.realized_pnl} currency={h.currency} /></td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
