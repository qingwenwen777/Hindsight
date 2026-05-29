import { formatPercent, pnlDirection } from "@/lib/format";
import { cn } from "@/lib/utils";

interface PercentBadgeProps {
  value: string | number | null | undefined;
  className?: string;
}

/**
 * 百分比小标签（设计文档 8.5 <PercentBadge>）。
 * 背景为对应涨跌色的低透明度。
 */
export function PercentBadge({ value, className }: PercentBadgeProps) {
  const dir = pnlDirection(value);
  const cls =
    dir === "up"
      ? "text-up bg-up/10"
      : dir === "down"
        ? "text-down bg-down/10"
        : "text-secondary bg-elevated";
  return (
    <span
      className={cn(
        "tnum inline-flex items-center rounded-sm px-1.5 py-0.5 text-caption font-medium",
        cls,
        className,
      )}
    >
      {formatPercent(value, { sign: true })}
    </span>
  );
}
