import { formatMoney, formatPercent, pnlDirection } from "@/lib/format";
import { cn } from "@/lib/utils";

interface PnLProps {
  value: string | number | null | undefined;
  currency?: string;
  /** 显示为百分比还是金额 */
  mode?: "money" | "percent";
  className?: string;
}

/**
 * 盈亏文字（设计文档 8.5 <PnL>）。
 * 自动按 colorScheme 上色（语义 token up/down），带 +/- 号和 tabular-nums。
 */
export function PnL({ value, currency = "JPY", mode = "money", className }: PnLProps) {
  const dir = pnlDirection(value);
  const colorClass = dir === "up" ? "text-up" : dir === "down" ? "text-down" : "text-secondary";
  const text =
    mode === "percent"
      ? formatPercent(value, { sign: true })
      : formatMoney(value, currency, { sign: true });
  return <span className={cn("tnum", colorClass, className)}>{text}</span>;
}
