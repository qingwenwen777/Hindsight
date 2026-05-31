"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { FadeIn, staggerDelay } from "@/components/ui/fade-in";
import { RefetchIndicator } from "@/components/ui/refetch-indicator";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate, formatMoney, formatQuantity } from "@/lib/format";
import { useT } from "@/lib/i18n/use-t";
import { useTransactions } from "@/lib/hooks/use-portfolio";

export default function TransactionsPage() {
  const { t } = useT();
  const { data: txs, isLoading, isFetching } = useTransactions();

  return (
    <div className="space-y-6">
      <RefetchIndicator active={isFetching && !isLoading} />
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-h1 text-primary">{t("tx.title")}</h1>
          <p className="text-small text-secondary">{t("tx.subtitle")}</p>
        </div>
        <Link href="/transactions/new">
          <Button>{t("tx.recordTrade")}</Button>
        </Link>
      </div>

      <Card className="overflow-hidden">
        <table className="w-full text-small">
          <thead>
            <tr className="border-b border-border-subtle text-caption text-secondary">
              <th className="px-4 py-3 text-left">{t("tx.col.date")}</th>
              <th className="px-4 py-3 text-left">{t("tx.col.side")}</th>
              <th className="px-4 py-3 text-right">{t("tx.col.qty")}</th>
              <th className="px-4 py-3 text-right">{t("tx.col.price")}</th>
              <th className="px-4 py-3 text-right">{t("tx.col.fees")}</th>
              <th className="px-4 py-3 text-center">{t("tx.col.journal")}</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              [0, 1, 2, 3, 4].map((i) => (
                <tr key={i} className="border-b border-border-subtle/50">
                  <td className="px-4 py-3"><Skeleton className="h-4 w-24" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-12" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-14 ml-auto" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-16 ml-auto" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-14 ml-auto" /></td>
                  <td className="px-4 py-3"><Skeleton className="mx-auto h-4 w-10" /></td>
                </tr>
              ))
            ) : !txs || txs.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-12 text-center text-secondary">
                  {t("tx.empty")}
                  <Link href="/transactions/new" className="text-primary underline underline-offset-2 hover:text-secondary">
                    {t("tx.goRecord")}
                  </Link>
                </td>
              </tr>
            ) : (
              txs.map((tx, i) => {
                const fees =
                  Number(tx.commission) + Number(tx.tax) + Number(tx.other_fees);
                return (
                  <FadeIn
                    as="tr"
                    key={tx.id}
                    delay={staggerDelay(i)}
                    className="border-b border-border-subtle/50 transition-colors duration-150 hover:bg-elevated"
                  >
                    <td className="tnum px-4 py-3 text-primary">{formatDate(tx.trade_date)}</td>
                    <td className="px-4 py-3">
                      <span className={tx.type === "BUY" ? "text-up" : "text-down"}>
                        {tx.type === "BUY" ? t("tx.buy") : t("tx.sell")}
                      </span>
                    </td>
                    <td className="tnum px-4 py-3 text-right text-primary">
                      {formatQuantity(tx.quantity)}
                    </td>
                    <td className="tnum px-4 py-3 text-right text-primary">
                      {formatMoney(tx.price, tx.currency)}
                    </td>
                    <td className="tnum px-4 py-3 text-right text-secondary">
                      {formatMoney(fees, tx.currency)}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {tx.journal_id ? (
                        <Link
                          href={`/journals/${tx.journal_id}`}
                          className="text-primary underline underline-offset-2 hover:text-secondary"
                        >
                          {t("tx.view")}
                        </Link>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                  </FadeIn>
                );
              })
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
