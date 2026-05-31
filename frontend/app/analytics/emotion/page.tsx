"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { EMOTIONS } from "@/components/forms/emotion-picker";
import { api } from "@/lib/api/client";
import { useT, type TFunc } from "@/lib/i18n/use-t";

interface EmotionRow {
  emotion: string;
  samples: number;
  wins: number;
  win_rate: number;
  win_rate_pct: number;
  avg_return_pct: string | null;
  profit_loss_ratio: number | null;
}

interface AuditData {
  by_emotion: EmotionRow[];
  conclusions: string[];
}

function emotionLabel(t: TFunc, value: string) {
  const e = EMOTIONS.find((x) => x.value === value);
  return e ? `${e.emoji} ${t(`form.emotion.${e.value}`)}` : value;
}

export default function EmotionAuditPage() {
  const { t } = useT();
  const { data, isLoading } = useQuery({
    queryKey: ["emotion-audit"],
    queryFn: async () => (await api.get<AuditData>("/reports/emotion-audit")).data,
  });

  const chartData = (data?.by_emotion ?? []).map((r) => ({
    name: emotionLabel(t, r.emotion),
    winRate: r.win_rate_pct,
    samples: r.samples,
  }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-h1 text-primary">{t("emotion.title")}</h1>
        <p className="text-small text-secondary">
          {t("emotion.subtitle")}
        </p>
      </div>

      {/* 结论文案 */}
      {data?.conclusions && data.conclusions.length > 0 && (
        <div className="space-y-1 rounded-md border border-warn/40 bg-warn/10 p-3">
          {data.conclusions.map((c, i) => (
            <p key={i} className="text-small text-warn">
              {c}
            </p>
          ))}
        </div>
      )}

      <section>
        <h2 className="border-b border-border-default pb-2 text-title font-medium text-primary">
          {t("emotion.winRateChart")}
        </h2>
        <div className="pt-4">
          {isLoading ? (
            <div className="skeleton h-64 rounded-md" />
          ) : chartData.length === 0 ? (
            <div className="flex h-64 items-center justify-center text-secondary">
              {t("emotion.noData")}
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart
                data={chartData}
                margin={{ top: 8, right: 8, bottom: 4, left: -8 }}
                barCategoryGap="45%"
              >
                {/* 仅保留横向网格，去掉竖向网格线，减少视觉噪音 */}
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="var(--border-default)"
                  vertical={false}
                />
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
                  formatter={(v: number) => [`${v}%`, t("emotion.col.winRate")]}
                  contentStyle={{
                    background: "var(--bg-elevated)",
                    border: "1px solid var(--border-default)",
                    borderRadius: 8,
                    color: "var(--text-primary)",
                    fontSize: 12,
                  }}
                />
                {/* 50% 掷硬币基准线，给柱子高低一个参照锚点 */}
                <ReferenceLine
                  y={50}
                  stroke="var(--border-strong)"
                  strokeDasharray="4 4"
                  label={{
                    value: "50%",
                    position: "right",
                    fill: "var(--text-tertiary)",
                    fontSize: 10,
                  }}
                />
                <Bar dataKey="winRate" radius={[3, 3, 0, 0]} maxBarSize={64}>
                  {chartData.map((entry, i) => (
                    <Cell
                      key={i}
                      fill={entry.winRate >= 50 ? "var(--up)" : "var(--down)"}
                      fillOpacity={0.85}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </section>

      <section>
        <h2 className="text-title font-medium text-primary">{t("emotion.detail")}</h2>
        <table className="mt-3 w-full text-small">
          <thead>
            <tr className="border-y border-border-default label-caps">
              <th className="px-2 py-2 text-left font-normal">{t("emotion.col.emotion")}</th>
              <th className="px-2 py-2 text-right font-normal">{t("emotion.col.samples")}</th>
              <th className="px-2 py-2 text-right font-normal">{t("emotion.col.winRate")}</th>
              <th className="px-2 py-2 text-right font-normal">{t("emotion.col.avgReturn")}</th>
              <th className="px-2 py-2 text-right font-normal">{t("emotion.col.plRatio")}</th>
            </tr>
          </thead>
          <tbody>
            {(data?.by_emotion ?? []).map((r) => (
              <tr key={r.emotion} className="border-b border-border-subtle">
                <td className="px-2 py-2 text-primary">{emotionLabel(t, r.emotion)}</td>
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
      </section>
    </div>
  );
}
