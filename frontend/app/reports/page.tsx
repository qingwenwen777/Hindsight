"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api/client";
import { formatMoney } from "@/lib/format";
import { useT } from "@/lib/i18n/use-t";
import { useUiStore } from "@/lib/store/ui-store";

interface PeriodReport {
  period: string;
  currency: string;
  buy_count: number;
  sell_count: number;
  total_buy_amount: string;
  total_sell_amount: string;
  total_fees: string;
  symbols_traded: string[];
  is_estimated: boolean;
}

interface FailureCase {
  transaction_id: number;
  symbol: string;
  name: string;
  trade_date: string;
  return_30d_pct: string;
  emotion: string | null;
  thesis: string | null;
}

export default function ReportsPage() {
  const { t } = useT();
  const baseCurrency = useUiStore((s) => s.baseCurrency);
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);

  const { data: report, refetch } = useQuery({
    queryKey: ["report-monthly", year, month, baseCurrency],
    queryFn: async () =>
      (await api.get<PeriodReport>(`/reports/monthly?year=${year}&month=${month}&currency=${baseCurrency}`)).data,
  });

  const { data: failures } = useQuery({
    queryKey: ["report-failures"],
    queryFn: async () => (await api.get<FailureCase[]>("/reports/failures")).data,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-h1 text-primary">{t("reports.title")}</h1>
        <p className="text-small text-secondary">{t("reports.subtitle")}</p>
      </div>

      <section>
        <div className="flex flex-row items-center justify-between border-b border-border-default pb-2">
          <h2 className="text-title font-medium text-primary">{t("reports.monthly")}</h2>
          <div className="flex items-center gap-2">
            <Input
              type="number"
              className="tnum w-24"
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
            />
            <Input
              type="number"
              className="tnum w-16"
              value={month}
              min={1}
              max={12}
              onChange={(e) => setMonth(Number(e.target.value))}
            />
            <Button size="sm" onClick={() => refetch()}>
              {t("reports.query")}
            </Button>
          </div>
        </div>
        <div className="pt-4">
          {report ? (
            <div className="grid grid-cols-2 divide-x divide-y divide-border-subtle border-y border-border-default md:grid-cols-3 md:divide-y-0">
              <Stat label={t("reports.buyCount")} value={String(report.buy_count)} />
              <Stat label={t("reports.sellCount")} value={String(report.sell_count)} />
              <Stat label={t("reports.symbolsTraded")} value={String(report.symbols_traded.length)} />
              <Stat label={t("reports.buyAmount")} value={formatMoney(report.total_buy_amount, report.currency)} />
              <Stat label={t("reports.sellAmount")} value={formatMoney(report.total_sell_amount, report.currency)} />
              <Stat label={t("reports.totalFees")} value={formatMoney(report.total_fees, report.currency)} />
            </div>
          ) : (
            <div className="skeleton h-24 rounded-md" />
          )}
        </div>
      </section>

      <section>
        <h2 className="text-title font-medium text-primary">{t("reports.failureLib")}</h2>
        <div className="pt-3">
          {!failures || failures.length === 0 ? (
            <p className="border-y border-border-default py-6 text-center text-small text-secondary">{t("reports.noFailures")}</p>
          ) : (
            <table className="w-full text-small">
              <thead>
                <tr className="border-y border-border-default label-caps">
                  <th className="px-2 py-2 text-left font-normal">{t("reports.col.symbol")}</th>
                  <th className="px-2 py-2 text-left font-normal">{t("reports.col.date")}</th>
                  <th className="px-2 py-2 text-right font-normal">{t("reports.col.return30d")}</th>
                  <th className="px-2 py-2 text-left font-normal">{t("reports.col.emotion")}</th>
                  <th className="px-2 py-2 text-left font-normal">{t("reports.col.thesis")}</th>
                </tr>
              </thead>
              <tbody>
                {failures.map((c) => (
                  <tr key={c.transaction_id} className="border-b border-border-subtle">
                    <td className="px-2 py-2 text-primary">
                      {c.name} <span className="tnum text-secondary">{c.symbol}</span>
                    </td>
                    <td className="tnum px-2 py-2 text-secondary">{c.trade_date}</td>
                    <td className="tnum px-2 py-2 text-right text-down">
                      {Number(c.return_30d_pct).toFixed(1)}%
                    </td>
                    <td className="px-2 py-2 text-secondary">{c.emotion ?? "—"}</td>
                    <td className="max-w-xs truncate px-2 py-2 text-secondary">{c.thesis ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="px-4 py-4">
      <div className="label-caps">{label}</div>
      <div className="tnum mt-2 text-mono-lg text-primary">{value}</div>
    </div>
  );
}
