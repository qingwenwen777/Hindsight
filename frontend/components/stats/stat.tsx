import { ArrowDown, ArrowUp } from "lucide-react";

import { cn } from "@/lib/utils";

interface StatProps {
  label: string;
  /** 主值（已格式化的字符串） */
  value: string;
  /** 副值（如对比基准、TWR 标注） */
  sub?: string;
  /** 涨跌方向，决定颜色与箭头 */
  direction?: "up" | "down" | "flat";
  /** 主值是否着色（默认仅 sub 显示涨跌） */
  colorValue?: boolean;
}

/**
 * 关键数字单元（设计文档 8.5 <Stat>）。
 * label + 大号等宽数字 + 涨跌色 + 箭头 + 副值。
 */
export function Stat({ label, value, sub, direction = "flat", colorValue = false }: StatProps) {
  const colorClass =
    direction === "up" ? "text-up" : direction === "down" ? "text-down" : "text-primary";

  return (
    <div className="rounded-lg border border-border-subtle bg-surface p-4">
      <div className="text-caption text-secondary">{label}</div>
      <div className={cn("tnum mt-2 text-display", colorValue ? colorClass : "text-primary")}>
        {value}
      </div>
      {sub && (
        <div className={cn("tnum mt-1 flex items-center gap-1 text-small", colorClass)}>
          {direction === "up" && <ArrowUp className="h-3 w-3" />}
          {direction === "down" && <ArrowDown className="h-3 w-3" />}
          <span>{sub}</span>
        </div>
      )}
    </div>
  );
}
