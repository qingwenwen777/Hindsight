"use client";

import { useState } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Sector } from "recharts";

import { useT } from "@/lib/i18n/use-t";

interface ExposureSlice {
  key: string;
  name: string;
  value: string;
  weight_pct: number;
  over_threshold: boolean;
}

interface DonutExposureProps {
  slices: ExposureSlice[];
  height?: number;
}

/**
 * 优雅的环形图配色：低饱和、和谐的现代色板（参考 Tailwind 500/400 调性），
 * 避免刺眼的高饱和原色；超阈值切片不再用刺眼描边，改为图例侧的柔和提示点。
 */
const PALETTE = [
  "#6366F1", // indigo
  "#14B8A6", // teal
  "#F59E0B", // amber
  "#EC4899", // pink
  "#0EA5E9", // sky
  "#8B5CF6", // violet
  "#10B981", // emerald
  "#F43F5E", // rose
  "#64748B", // slate
  "#EAB308", // yellow
];

function renderActiveShape(props: any) {
  const { cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill } = props;
  return (
    <g>
      {/* 高亮时切片微微外扩，柔和不跳动 */}
      <Sector
        cx={cx}
        cy={cy}
        innerRadius={innerRadius}
        outerRadius={outerRadius + 6}
        startAngle={startAngle}
        endAngle={endAngle}
        fill={fill}
        cornerRadius={6}
      />
    </g>
  );
}

/** 暴露/集中度环形图：低饱和现代配色 + 中心总览 + 交互式图例。 */
export function DonutExposure({ slices, height = 300 }: DonutExposureProps) {
  const { t } = useT();
  const [active, setActive] = useState<number | null>(null);

  if (!slices || slices.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-xl border border-dashed border-border-subtle text-secondary"
        style={{ height }}
      >
        {t("exposure.noData")}
      </div>
    );
  }

  const data = slices.map((s, i) => ({
    name: s.name,
    value: s.weight_pct,
    over: s.over_threshold,
    color: PALETTE[i % PALETTE.length],
  }));

  // 中心显示：悬停时显示该切片，否则显示占比最高的切片
  const topIndex =
    active != null ? active : data.reduce((best, d, i, arr) => (d.value > arr[best].value ? i : best), 0);
  const center = data[topIndex];

  return (
    <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-center sm:gap-8">
      {/* 环形图 + 中心总览 */}
      <div className="relative shrink-0" style={{ width: height, height }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              innerRadius="62%"
              outerRadius="86%"
              paddingAngle={data.length > 1 ? 3 : 0}
              cornerRadius={6}
              stroke="var(--bg-surface)"
              strokeWidth={3}
              startAngle={90}
              endAngle={-270}
              activeIndex={active ?? undefined}
              activeShape={renderActiveShape}
              onMouseEnter={(_, i) => setActive(i)}
              onMouseLeave={() => setActive(null)}
              isAnimationActive
              animationDuration={600}
            >
              {data.map((entry) => (
                <Cell key={entry.name} fill={entry.color} style={{ outline: "none" }} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>

        {/* 中心叠加：占比 + 名称 */}
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className="tnum text-display font-semibold text-primary">
            {center.value.toFixed(1)}%
          </span>
          <span className="mt-1 max-w-[60%] truncate text-caption text-tertiary">{center.name}</span>
        </div>
      </div>

      {/* 交互式图例 */}
      <ul className="flex w-full max-w-xs flex-col gap-1.5">
        {data.map((entry, i) => {
          const isActive = active === i;
          return (
            <li
              key={entry.name}
              onMouseEnter={() => setActive(i)}
              onMouseLeave={() => setActive(null)}
              className={`flex cursor-default items-center gap-2.5 rounded-lg px-2.5 py-1.5 transition-colors ${
                isActive ? "bg-elevated" : ""
              }`}
            >
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: entry.color }}
              />
              <span className="min-w-0 flex-1 truncate text-body text-secondary">{entry.name}</span>
              {entry.over && (
                <span className="shrink-0 rounded-full bg-warn/15 px-1.5 py-0.5 text-[10px] font-medium text-warn">
                  {t("exposure.overThreshold")}
                </span>
              )}
              <span className="tnum shrink-0 text-body font-medium text-primary">
                {entry.value.toFixed(1)}%
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
