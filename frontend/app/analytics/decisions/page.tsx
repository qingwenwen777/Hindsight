"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { api } from "@/lib/api/client";
import { useT } from "@/lib/i18n/use-t";

interface CalibrationRow {
  confidence: number;
  implied_win_rate_pct: number;
  actual_win_rate_pct: number;
  samples: number;
  avg_return_pct: string | null;
  gap_pct: number;
}
interface CalibrationData {
  by_confidence: CalibrationRow[];
  conclusions: string[];
}

interface CategoryRow {
  category: string;
  samples: number;
  wins: number;
  win_rate_pct: number;
  avg_return_pct: string | null;
  profit_loss_ratio: number | null;
}
interface CategoryData {
  by_category: CategoryRow[];
  conclusions: string[];
}

const tooltipStyle = {
  background: "var(--bg-elevated)",
  border: "1px solid var(--border-default)",
  borderRadius: 8,
  color: "var(--text-primary)",
  fontSize: 12,
};

export default function DecisionQualityPage() {
  const { t } = useT();

  const { data: calib, isLoading: calibLoading } = useQuery({
    queryKey: ["decision-calibration"],
    queryFn: async () => (await api.get<CalibrationData>("/reports/decision-calibration")).data,
  });
  const { data: cats, isLoading: catsLoading } = useQuery({
    queryKey: ["decision-categories"],
    queryFn: async () => (await api.get<CategoryData>("/reports/decision-categories")).data,
  });

  const calibChart = (calib?.by_confidence ?? []).map((r) => ({
    name: `${r.confidence}/5`,
    implied: r.implied_win_rate_pct,
    actual: r.actual_win_rate_pct,
    samples: r.samples,
  }));

  const catChart = (cats?.by_category ?? []).map((r) => ({
    name: t(`decisions.cat.${r.category}`),
    avgReturn: r.avg_return_pct != null ? Number(Number(r.avg_return_pct).toFixed(2)) : 0,
    winRate: r.win_rate_pct,
  }));

  const allConclusions = [...(calib?.conclusions ?? []), ...(cats?.conclusions ?? [])];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-h1 text-primary">{t("decisions.title")}</h1>
        <p className="text-small text-secondary">{t("decisions.subtitle")}</p>
      </div>

      {/* 结论文案（合并校准 + 类别） */}
      {allConclusions.length > 0 && (
        <div className="space-y-1 rounded-md border border-warn/40 bg-warn/10 p-3">
          {allConclusions.map((c, i) => (
            <p key={i} className="text-small text-warn">
              {c}
            </p>
          ))}
        </div>
      )}

      {/* 信心校准 */}
      <section>
        <h2 className="border-b border-border-default pb-2 text-title font-medium text-primary">
          {t("decisions.calibTitle")}
        </h2>
        <p className="pt-2 text-meta text-tertiary">{t("decisions.calibHint")}</p>
        <div className="pt-4">
          {calibLoading ? (
            <div className="skeleton h-64 rounded-md" />
          ) : calibChart.length === 0 ? (
            <div className="flex h-48 items-center justify-center text-secondary">
              {t("decisions.noData")}
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={calibChart} margin={{ top: 8, right: 8, bottom: 4, left: -8 }} barGap={4}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-default)" vertical={false} />
                <XAxis
                  dataKey="name"
                  tick={{ fill: "var(--text-secondary)", fontSize: 12 }}
                  axisLine={{ stroke: "var(--border-default)" }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: "var(--text-tertiary)", fontSize: 11 }}
                  domain={[0, 100]}
                  ticks={[0, 25, 50, 75, 100]}
                  unit="%"
                  axisLine={false}
                  tickLine={false}
                  width={40}
                />
                <Tooltip
                  cursor={{ fill: "var(--text-primary)", fillOpacity: 0.04 }}
                  contentStyle={tooltipStyle}
                  formatter={(v: number, n: string) => [
                    `${v}%`,
                    n === "implied" ? t("decisions.implied") : t("decisions.actual"),
                  ]}
                />
                <Legend
                  formatter={(v) => (v === "implied" ? t("decisions.implied") : t("decisions.actual"))}
                  wrapperStyle={{ fontSize: 12, color: "var(--text-tertiary)" }}
                />
                <Bar dataKey="implied" fill="var(--text-tertiary)" fillOpacity={0.5} radius={[3, 3, 0, 0]} maxBarSize={40} />
                <Bar dataKey="actual" fill="var(--accent)" fillOpacity={0.85} radius={[3, 3, 0, 0]} maxBarSize={40} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {calibChart.length > 0 && (
          <table className="mt-4 w-full text-small">
            <thead>
              <tr className="border-y border-border-default label-caps">
                <th className="px-2 py-2 text-left font-normal">{t("decisions.col.confidence")}</th>
                <th className="px-2 py-2 text-right font-normal">{t("decisions.col.samples")}</th>
                <th className="px-2 py-2 text-right font-normal">{t("decisions.implied")}</th>
                <th className="px-2 py-2 text-right font-normal">{t("decisions.actual")}</th>
                <th className="px-2 py-2 text-right font-normal">{t("decisions.col.gap")}</th>
                <th className="px-2 py-2 text-right font-normal">{t("decisions.col.avgReturn")}</th>
              </tr>
            </thead>
            <tbody>
              {(calib?.by_confidence ?? []).map((r) => (
                <tr key={r.confidence} className="border-b border-border-subtle">
                  <td className="px-2 py-2 text-primary">{r.confidence}/5</td>
                  <td className="tnum px-2 py-2 text-right text-secondary">{r.samples}</td>
                  <td className="tnum px-2 py-2 text-right text-tertiary">{r.implied_win_rate_pct}%</td>
                  <td className="tnum px-2 py-2 text-right text-primary">{r.actual_win_rate_pct}%</td>
                  <td
                    className={`tnum px-2 py-2 text-right ${
                      r.gap_pct < 0 ? "text-down" : r.gap_pct > 0 ? "text-up" : "text-secondary"
                    }`}
                  >
                    {r.gap_pct > 0 ? "+" : ""}
                    {r.gap_pct}%
                  </td>
                  <td className="tnum px-2 py-2 text-right text-secondary">
                    {r.avg_return_pct ? `${Number(r.avg_return_pct).toFixed(2)}%` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* 决策类别聚合 */}
      <section>
        <h2 className="border-b border-border-default pb-2 text-title font-medium text-primary">
          {t("decisions.catTitle")}
        </h2>
        <p className="pt-2 text-meta text-tertiary">{t("decisions.catHint")}</p>
        <div className="pt-4">
          {catsLoading ? (
            <div className="skeleton h-64 rounded-md" />
          ) : catChart.length === 0 ? (
            <div className="flex h-48 items-center justify-center text-secondary">
              {t("decisions.noData")}
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={catChart} margin={{ top: 8, right: 8, bottom: 4, left: -8 }} barCategoryGap="40%">
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-default)" vertical={false} />
                <XAxis
                  dataKey="name"
                  tick={{ fill: "var(--text-secondary)", fontSize: 12 }}
                  axisLine={{ stroke: "var(--border-default)" }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: "var(--text-tertiary)", fontSize: 11 }}
                  unit="%"
                  axisLine={false}
                  tickLine={false}
                  width={44}
                />
                <Tooltip
                  cursor={{ fill: "var(--text-primary)", fillOpacity: 0.04 }}
                  contentStyle={tooltipStyle}
                  formatter={(v: number) => [`${v}%`, t("decisions.col.avgReturn")]}
                />
                <ReferenceLine y={0} stroke="var(--border-strong)" />
                <Bar dataKey="avgReturn" radius={[3, 3, 0, 0]} maxBarSize={64}>
                  {catChart.map((entry, i) => (
                    <Cell key={i} fill={entry.avgReturn >= 0 ? "var(--up)" : "var(--down)"} fillOpacity={0.85} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {catChart.length > 0 && (
          <table className="mt-4 w-full text-small">
            <thead>
              <tr className="border-y border-border-default label-caps">
                <th className="px-2 py-2 text-left font-normal">{t("decisions.col.category")}</th>
                <th className="px-2 py-2 text-right font-normal">{t("decisions.col.samples")}</th>
                <th className="px-2 py-2 text-right font-normal">{t("decisions.col.winRate")}</th>
                <th className="px-2 py-2 text-right font-normal">{t("decisions.col.avgReturn")}</th>
                <th className="px-2 py-2 text-right font-normal">{t("decisions.col.plRatio")}</th>
              </tr>
            </thead>
            <tbody>
              {(cats?.by_category ?? []).map((r) => (
                <tr key={r.category} className="border-b border-border-subtle">
                  <td className="px-2 py-2 text-primary">{t(`decisions.cat.${r.category}`)}</td>
                  <td className="tnum px-2 py-2 text-right text-secondary">{r.samples}</td>
                  <td className="tnum px-2 py-2 text-right text-primary">{r.win_rate_pct}%</td>
                  <td className="tnum px-2 py-2 text-right text-secondary">
                    {r.avg_return_pct ? `${Number(r.avg_return_pct).toFixed(2)}%` : "—"}
                  </td>
                  <td className="tnum px-2 py-2 text-right text-secondary">
                    {r.profit_loss_ratio != null ? r.profit_loss_ratio.toFixed(2) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <p className="text-caption text-muted">{t("decisions.footnote")}</p>
    </div>
  );
}
