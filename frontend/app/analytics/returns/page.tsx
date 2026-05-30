"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Stat } from "@/components/stats/stat";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatMoney, formatPercent, pnlDirection } from "@/lib/format";
import { useT } from "@/lib/i18n/use-t";
import { useEquityCurve, useReturns, useRiskMetrics } from "@/lib/hooks/use-analytics";

const tooltipStyle = {
  background: "var(--bg-elevated)",
  border: "1px solid var(--border-default)",
  borderRadius: 8,
  color: "var(--text-primary)",
  fontSize: 12,
};

export default function ReturnsPage() {
  const { t } = useT();
  const { data: irr } = useReturns("IRR");
  const { data: twr } = useReturns("TWR");
  const { data: risk } = useRiskMetrics();
  const { data: equity } = useEquityCurve();

  const irrPct = irr?.annualized_pct ? Number(irr.annualized_pct) : null;
  const twrPct = twr?.twr_pct ? Number(twr.twr_pct) : null;

  const equityData =
    equity?.dates.map((d, i) => ({ date: d, value: equity.normalized[i] })) ?? [];
  const ddData = risk?.drawdown_series ?? [];

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-display text-secondary">{t("returns.title")}</h1>
        <p className="mt-2 text-meta text-tertiary">{t("returns.subtitle")}</p>
      </div>

      {/* 指标卡 */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
        <Stat
          label={t("returns.irr")}
          value={irrPct != null ? formatPercent(irrPct, { sign: true }) : "—"}
          colorValue
          direction={pnlDirection(irrPct)}
        />
        <Stat
          label={t("returns.twr")}
          value={twrPct != null ? formatPercent(twrPct, { sign: true }) : "—"}
          colorValue
          direction={pnlDirection(twrPct)}
        />
        <Stat
          label={t("returns.annualized")}
          value={risk?.available ? formatPercent(risk.annualized_return_pct, { sign: true }) : "—"}
          colorValue
          direction={pnlDirection(risk?.annualized_return_pct)}
        />
        <Stat
          label={t("returns.maxDrawdown")}
          value={risk?.available ? formatPercent(risk.max_drawdown_pct) : "—"}
          colorValue
          direction={risk?.max_drawdown_pct ? "down" : "flat"}
        />
        <Stat label={t("returns.sharpe")} value={risk?.available ? String(risk.sharpe) : "—"} />
        <Stat label={t("returns.calmar")} value={risk?.available ? String(risk.calmar) : "—"} />
      </div>

      {/* 净值曲线 */}
      <Card>
        <CardHeader>
          <CardTitle>{t("returns.equityNormalized")}</CardTitle>
        </CardHeader>
        <CardContent>
          {equityData.length < 2 ? (
            <div className="flex h-64 items-center justify-center rounded-md border border-dashed border-border-default text-tertiary">
              {t("returns.equityInsufficient")}
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={equityData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-default)" />
                <XAxis dataKey="date" tick={{ fill: "var(--text-tertiary)", fontSize: 11 }} minTickGap={40} />
                <YAxis tick={{ fill: "var(--text-tertiary)", fontSize: 11 }} domain={["auto", "auto"]} />
                <Tooltip contentStyle={tooltipStyle} />
                <Line type="monotone" dataKey="value" stroke="var(--up)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* 回撤水下图 */}
      <Card>
        <CardHeader>
          <CardTitle>{t("returns.drawdownChart")}</CardTitle>
        </CardHeader>
        <CardContent>
          {ddData.length < 2 ? (
            <div className="flex h-48 items-center justify-center rounded-md border border-dashed border-border-default text-tertiary">
              {t("returns.noDrawdown")}
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={ddData}>
                <defs>
                  <linearGradient id="ddFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--down)" stopOpacity={0.05} />
                    <stop offset="100%" stopColor="var(--down)" stopOpacity={0.3} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-default)" />
                <XAxis dataKey="date" tick={{ fill: "var(--text-tertiary)", fontSize: 11 }} minTickGap={40} />
                <YAxis tick={{ fill: "var(--text-tertiary)", fontSize: 11 }} unit="%" />
                <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => `${v}%`} />
                <Area
                  type="monotone"
                  dataKey="drawdown_pct"
                  stroke="var(--down)"
                  strokeWidth={1.5}
                  fill="url(#ddFill)"
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <p className="text-caption text-muted">
        {t("returns.footnote")}
      </p>
    </div>
  );
}
