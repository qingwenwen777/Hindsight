"use client";

import Link from "next/link";

import { PnL } from "@/components/stats/pnl";
import { Card } from "@/components/ui/card";
import { formatMoney, formatQuantity } from "@/lib/format";
import { useT } from "@/lib/i18n/use-t";
import { useHoldings } from "@/lib/hooks/use-portfolio";

export default function HoldingsPage() {
  const { t } = useT();
  const { data: holdings, isLoading } = useHoldings();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-h1 text-primary">{t("holdings.title")}</h1>
        <p className="text-small text-secondary">{t("holdings.subtitle")}</p>
      </div>

      <Card className="overflow-hidden">
        <table className="w-full text-small">
          <thead>
            <tr className="border-b border-border-subtle text-caption text-secondary">
              <th className="px-4 py-3 text-left">{t("holdings.col.symbol")}</th>
              <th className="px-4 py-3 text-right">{t("holdings.col.shares")}</th>
              <th className="px-4 py-3 text-right">{t("holdings.col.avgCost")}</th>
              <th className="px-4 py-3 text-right">{t("holdings.col.price")}</th>
              <th className="px-4 py-3 text-right">{t("holdings.col.marketValue")}</th>
              <th className="px-4 py-3 text-right">{t("holdings.col.unrealized")}</th>
              <th className="px-4 py-3 text-right">{t("holdings.col.realized")}</th>
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
                  {t("holdings.empty")}
                  <Link href="/transactions/new" className="text-primary underline underline-offset-2 hover:text-secondary">
                    {t("holdings.goRecord")}
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
