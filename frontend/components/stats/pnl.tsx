"use client";

import { formatMoney, formatPercent, pnlDirection } from "@/lib/format";
import { useFlashOnChange } from "@/lib/hooks/use-flash-on-change";
import { cn } from "@/lib/utils";

interface PnLProps {
  value: string | number | null | undefined;
  currency?: string;
  /** 显示为百分比还是金额 */
  mode?: "money" | "percent";
  /** 数值更新时背景闪一下对应涨跌色（行情滚动场景用），默认开启 */
  flash?: boolean;
  className?: string;
}

/**
 * 盈亏文字（设计文档 8.5 <PnL>）。
 * 自动按 colorScheme 上色（语义 token up/down），带 +/- 号和 tabular-nums。
 * 数值更新时背景闪一下对应涨跌色（约 440ms 淡出），克制提示"变了"。
 */
export function PnL({ value, currency = "JPY", mode = "money", flash = true, className }: PnLProps) {
  const dir = pnlDirection(value);
  const colorClass = dir === "up" ? "text-up" : dir === "down" ? "text-down" : "text-secondary";
  const num = value == null || value === "" ? null : Number(value);
  const flashDir = useFlashOnChange(flash ? num : null);
  const text =
    mode === "percent"
      ? formatPercent(value, { sign: true })
      : formatMoney(value, currency, { sign: true });
  return (
    <span
      className={cn(
        "tnum rounded-sm",
        colorClass,
        flashDir === "up" && "animate-flash-up",
        flashDir === "down" && "animate-flash-down",
        className,
      )}
    >
      {text}
    </span>
  );
}
