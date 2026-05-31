"use client";

import Link from "next/link";

import { PnL } from "@/components/stats/pnl";
import { FadeIn, staggerDelay } from "@/components/ui/fade-in";
import { RefetchIndicator } from "@/components/ui/refetch-indicator";
import { Skeleton } from "@/components/ui/skeleton";
import { formatMoney, formatQuantity } from "@/lib/format";
import { useT } from "@/lib/i18n/use-t";
import { useHoldings } from "@/lib/hooks/use-portfolio";

export default function HoldingsPage() {
  const { t } = useT();
  const { data: holdings, isLoading, isFetching } = useHoldings();

  return (
    <div className="space-y-6">
      <RefetchIndicator active={isFetching && !isLoading} />
      <div>
        <h1 className="text-h1 text-primary">{t("holdings.title")}</h1>
        <p className="text-small text-secondary">{t("holdings.subtitle")}</p>
      </div>

      <table className="w-full text-small">
        <thead>
          <tr className="border-y border-border-default label-caps">
            <th className="px-3 py-2 text-left font-normal">{t("holdings.col.symbol")}</th>
            <th className="px-3 py-2 text-right font-normal">{t("holdings.col.shares")}</th>
            <th className="px-3 py-2 text-right font-normal">{t("holdings.col.avgCost")}</th>
            <th className="px-3 py-2 text-right font-normal">{t("holdings.col.price")}</th>
            <th className="px-3 py-2 text-right font-normal">{t("holdings.col.marketValue")}</th>
            <th className="px-3 py-2 text-right font-normal">{t("holdings.col.unrealized")}</th>
            <th className="px-3 py-2 text-right font-normal">{t("holdings.col.realized")}</th>
          </tr>
        </thead>
        <tbody>
          {isLoading ? (
            [0, 1, 2, 3, 4].map((i) => (
              <tr key={i} className="border-b border-border-subtle">
                <td className="px-3 py-2.5"><Skeleton className="h-4 w-32" /></td>
                <td className="px-3 py-2.5"><Skeleton className="h-4 w-14 justify-self-end ml-auto" /></td>
                <td className="px-3 py-2.5"><Skeleton className="h-4 w-16 justify-self-end ml-auto" /></td>
                <td className="px-3 py-2.5"><Skeleton className="h-4 w-16 justify-self-end ml-auto" /></td>
                <td className="px-3 py-2.5"><Skeleton className="h-4 w-20 justify-self-end ml-auto" /></td>
                <td className="px-3 py-2.5"><Skeleton className="h-4 w-16 justify-self-end ml-auto" /></td>
                <td className="px-3 py-2.5"><Skeleton className="h-4 w-16 justify-self-end ml-auto" /></td>
              </tr>
            ))
          ) : !holdings || holdings.length === 0 ? (
            <tr>
              <td colSpan={7} className="px-3 py-12 text-center text-secondary">
                {t("holdings.empty")}
                <Link href="/transactions/new" className="text-primary underline underline-offset-2 hover:text-secondary">
                  {t("holdings.goRecord")}
                </Link>
              </td>
            </tr>
          ) : (
            holdings.map((h, i) => (
              <FadeIn
                as="tr"
                key={h.stock_id}
                delay={staggerDelay(i)}
                className="border-b border-border-subtle transition-colors duration-150 hover:bg-elevated/50"
              >
                <td className="px-3 py-2.5">
                  <Link href={`/stocks/${h.stock_id}`} className="text-primary hover:text-accent">
                    {h.name} <span className="tnum text-secondary">{h.symbol}</span>
                  </Link>
                </td>
                <td className="tnum px-3 py-2.5 text-right text-primary">{formatQuantity(h.shares)}</td>
                <td className="tnum px-3 py-2.5 text-right text-secondary">{formatMoney(h.avg_cost, h.currency)}</td>
                <td className="tnum px-3 py-2.5 text-right text-primary">{formatMoney(h.last_price, h.currency)}</td>
                <td className="tnum px-3 py-2.5 text-right text-primary">{formatMoney(h.market_value ?? h.cost_basis, h.currency)}</td>
                <td className="px-3 py-2.5 text-right"><PnL value={h.unrealized_pnl} currency={h.currency} /></td>
                <td className="px-3 py-2.5 text-right"><PnL value={h.realized_pnl} currency={h.currency} /></td>
              </FadeIn>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
