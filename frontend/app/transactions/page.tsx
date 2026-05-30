"use client";

import Link from "next/link";

import { PnL } from "@/components/stats/pnl";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { formatDate, formatMoney, formatQuantity } from "@/lib/format";
import { useTransactions } from "@/lib/hooks/use-portfolio";

export default function TransactionsPage() {
  const { data: txs, isLoading } = useTransactions();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-h1 text-primary">交易记录</h1>
          <p className="text-small text-secondary">所有买卖流水。</p>
        </div>
        <Link href="/transactions/new">
          <Button>录入交易</Button>
        </Link>
      </div>

      <Card className="overflow-hidden">
        <table className="w-full text-small">
          <thead>
            <tr className="border-b border-border-subtle text-caption text-secondary">
              <th className="px-4 py-3 text-left">日期</th>
              <th className="px-4 py-3 text-left">方向</th>
              <th className="px-4 py-3 text-right">数量</th>
              <th className="px-4 py-3 text-right">价格</th>
              <th className="px-4 py-3 text-right">费用</th>
              <th className="px-4 py-3 text-center">日志</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              [0, 1, 2].map((i) => (
                <tr key={i}>
                  <td colSpan={6} className="px-4 py-3">
                    <div className="h-6 animate-pulse rounded bg-elevated" />
                  </td>
                </tr>
              ))
            ) : !txs || txs.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-12 text-center text-secondary">
                  还没有交易，
                  <Link href="/transactions/new" className="text-primary underline underline-offset-2 hover:text-secondary">
                    去录入
                  </Link>
                </td>
              </tr>
            ) : (
              txs.map((t) => {
                const fees =
                  Number(t.commission) + Number(t.tax) + Number(t.other_fees);
                return (
                  <tr key={t.id} className="border-b border-border-subtle/50 hover:bg-elevated">
                    <td className="tnum px-4 py-3 text-primary">{formatDate(t.trade_date)}</td>
                    <td className="px-4 py-3">
                      <span className={t.type === "BUY" ? "text-up" : "text-down"}>
                        {t.type === "BUY" ? "买入" : "卖出"}
                      </span>
                    </td>
                    <td className="tnum px-4 py-3 text-right text-primary">
                      {formatQuantity(t.quantity)}
                    </td>
                    <td className="tnum px-4 py-3 text-right text-primary">
                      {formatMoney(t.price, t.currency)}
                    </td>
                    <td className="tnum px-4 py-3 text-right text-secondary">
                      {formatMoney(fees, t.currency)}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {t.journal_id ? (
                        <Link
                          href={`/journals/${t.journal_id}`}
                          className="text-primary underline underline-offset-2 hover:text-secondary"
                        >
                          查看
                        </Link>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
