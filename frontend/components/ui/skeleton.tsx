import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * 骨架占位块。底色 + 扫光（shimmer，定义在 globals.css 的 .skeleton）。
 * 用法：<Skeleton className="h-6 w-32" />，组合出与真实内容结构一致的占位。
 */
export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("skeleton", className)} {...props} />;
}

/** 文本行骨架：可指定行数，最后一行偏短更自然。 */
export function SkeletonText({
  lines = 3,
  className,
}: {
  lines?: number;
  className?: string;
}) {
  return (
    <div className={cn("space-y-2", className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={cn("h-3.5", i === lines - 1 ? "w-2/3" : "w-full")}
        />
      ))}
    </div>
  );
}

/** KPI 卡片骨架：与 <Stat> 结构一致（标签条 + 大数字）。 */
export function SkeletonStat() {
  return (
    <div className="card-shadow rounded-card border border-border-default bg-surface px-6 py-8">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="mt-3.5 h-9 w-32" />
    </div>
  );
}

/**
 * 表格行骨架。columns 指定每列宽度类（用于和真实列对齐），
 * align 控制单元格内占位块靠左/右。
 */
export function SkeletonRow({
  widths,
  className,
}: {
  widths: string[];
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex items-center gap-4 border-b border-border-subtle/50 px-4 py-3",
        className,
      )}
    >
      {widths.map((w, i) => (
        <Skeleton key={i} className={cn("h-4", w)} />
      ))}
    </div>
  );
}
