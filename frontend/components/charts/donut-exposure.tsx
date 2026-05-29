"use client";

import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

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

const PALETTE = ["#2962FF", "#26A69A", "#FF9800", "#AB47BC", "#EF5350", "#42A5F5", "#66BB6A", "#FFCA28"];

/** 暴露/集中度环形图（设计文档 8.6）。超阈值切片用警告色描边。 */
export function DonutExposure({ slices, height = 280 }: DonutExposureProps) {
  if (!slices || slices.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-md border border-dashed border-border-subtle text-secondary"
        style={{ height }}
      >
        暂无持仓数据
      </div>
    );
  }
  const data = slices.map((s) => ({ name: s.name, value: s.weight_pct, over: s.over_threshold }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          innerRadius="55%"
          outerRadius="80%"
          paddingAngle={2}
        >
          {data.map((entry, i) => (
            <Cell
              key={entry.name}
              fill={PALETTE[i % PALETTE.length]}
              stroke={entry.over ? "#FF9800" : "transparent"}
              strokeWidth={entry.over ? 2 : 0}
            />
          ))}
        </Pie>
        <Tooltip
          formatter={(v: number) => `${v}%`}
          contentStyle={{
            background: "var(--bg-elevated)",
            border: "1px solid var(--border-subtle)",
            borderRadius: 6,
            color: "var(--text-primary)",
            fontSize: 12,
          }}
        />
        <Legend wrapperStyle={{ fontSize: 12, color: "var(--text-secondary)" }} />
      </PieChart>
    </ResponsiveContainer>
  );
}
