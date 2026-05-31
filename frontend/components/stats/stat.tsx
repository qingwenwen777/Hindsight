import { AnimatedNumber } from "@/components/stats/animated-number";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface StatProps {
  label: string;
  /** 主值（已格式化的字符串）。loading 为 true 或未提供 numeric 时使用。 */
  value?: string;
  /** 可选：原始数值 + 格式化函数，提供则启用数字滚动（count-up）。 */
  numeric?: number | null;
  format?: (n: number) => string;
  /** 副值（如对比基准、TWR 标注） */
  sub?: string;
  /** 右上角徽章（如 YTD / 月度） */
  badge?: string;
  /** 涨跌方向，决定颜色 */
  direction?: "up" | "down" | "flat";
  /** 主值是否着色 */
  colorValue?: boolean;
  /** 加载中：渲染骨架占位替代数值 */
  loading?: boolean;
}

/**
 * KPI 卡片（Hindsight 风格）。
 * 大写字距标签 + 36px 等宽数字 + 涨跌色副值。
 * loading 时显示骨架；提供 numeric+format 时数值变化做平滑滚动。
 */
export function Stat({
  label,
  value,
  numeric,
  format,
  sub,
  badge,
  direction = "flat",
  colorValue = false,
  loading = false,
}: StatProps) {
  const colorClass =
    direction === "up" ? "text-up" : direction === "down" ? "text-down" : "text-tertiary";
  const valueCls = cn("tnum mt-3.5 text-kpi", colorValue ? colorClass : "text-primary");

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
      {loading ? (
        <Skeleton className="mt-3.5 h-9 w-32" />
      ) : numeric != null && format ? (
        <AnimatedNumber value={numeric} format={format} className={valueCls} />
      ) : (
        <div className={valueCls}>{value}</div>
      )}
      {sub && <div className={cn("tnum mt-2.5 text-meta", colorClass)}>{sub}</div>}
    </div>
  );
}
