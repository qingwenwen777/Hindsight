"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api/client";
import { formatMoney } from "@/lib/format";
import { useT } from "@/lib/i18n/use-t";

interface PeriodReport {
  period: string;
  buy_count: number;
  sell_count: number;
  total_buy_amount: string;
  total_sell_amount: string;
  total_fees: string;
  symbols_traded: string[];
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
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);

  const { data: report, refetch } = useQuery({
    queryKey: ["report-monthly", year, month],
    queryFn: async () =>
      (await api.get<PeriodReport>(`/reports/monthly?year=${year}&month=${month}`)).data,
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

      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>{t("reports.monthly")}</CardTitle>
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
        </CardHeader>
        <CardContent>
          {report ? (
            <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
              <Stat label={t("reports.buyCount")} value={String(report.buy_count)} />
              <Stat label={t("reports.sellCount")} value={String(report.sell_count)} />
              <Stat label={t("reports.symbolsTraded")} value={String(report.symbols_traded.length)} />
              <Stat label={t("reports.buyAmount")} value={formatMoney(report.total_buy_amount)} />
              <Stat label={t("reports.sellAmount")} value={formatMoney(report.total_sell_amount)} />
              <Stat label={t("reports.totalFees")} value={formatMoney(report.total_fees)} />
            </div>
          ) : (
            <div className="h-24 animate-pulse rounded-md bg-elevated" />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t("reports.failureLib")}</CardTitle>
        </CardHeader>
        <CardContent>
          {!failures || failures.length === 0 ? (
            <p className="py-6 text-center text-small text-secondary">{t("reports.noFailures")}</p>
          ) : (
            <table className="w-full text-small">
              <thead>
                <tr className="border-b border-border-subtle text-caption text-secondary">
                  <th className="px-2 py-2 text-left">{t("reports.col.symbol")}</th>
                  <th className="px-2 py-2 text-left">{t("reports.col.date")}</th>
                  <th className="px-2 py-2 text-right">{t("reports.col.return30d")}</th>
                  <th className="px-2 py-2 text-left">{t("reports.col.emotion")}</th>
                  <th className="px-2 py-2 text-left">{t("reports.col.thesis")}</th>
                </tr>
              </thead>
              <tbody>
                {failures.map((c) => (
                  <tr key={c.transaction_id} className="border-b border-border-subtle/50">
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
        </CardContent>
      </Card>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border-subtle bg-base p-3">
      <div className="text-caption text-secondary">{label}</div>
      <div className="tnum mt-1 text-mono-lg text-primary">{value}</div>
    </div>
  );
}
