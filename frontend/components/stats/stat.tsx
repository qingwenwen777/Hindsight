import { cn } from "@/lib/utils";

interface StatProps {
  label: string;
  /** 主值（已格式化的字符串） */
  value: string;
  /** 副值（如对比基准、TWR 标注） */
  sub?: string;
  /** 右上角徽章（如 YTD / 月度） */
  badge?: string;
  /** 涨跌方向，决定颜色 */
  direction?: "up" | "down" | "flat";
  /** 主值是否着色 */
  colorValue?: boolean;
}

/**
 * KPI 卡片（Hindsight 风格）。
 * 大写字距标签 + 36px 等宽数字 + 涨跌色副值。
 */
export function Stat({ label, value, sub, badge, direction = "flat", colorValue = false }: StatProps) {
  const colorClass =
    direction === "up" ? "text-up" : direction === "down" ? "text-down" : "text-tertiary";

  return (
    <div className="card-shadow rounded-card border border-border-default bg-surface px-6 py-8">
      <div className="flex items-center justify-between">
        <span className="label-caps">{label}</span>
        {badge && (
          <span className="rounded-badge border border-border-default bg-elevated px-1.5 py-0.5 text-badge font-medium text-secondary">
            {badge}
          </span>
        )}
      </div>
      <div className={cn("tnum mt-3.5 text-kpi", colorValue ? colorClass : "text-primary")}>
        {value}
      </div>
      {sub && <div className={cn("tnum mt-2.5 text-meta", colorClass)}>{sub}</div>}
    </div>
  );
}
