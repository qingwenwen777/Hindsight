"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

/** 单项延迟封顶：超过这一项后不再累加，避免长列表末尾出现太晚。 */
const MAX_STAGGER_INDEX = 12;
/** 每项递增延迟（ms）。 */
const STEP_MS = 28;

type FadeInProps = {
  /** 入场延迟（毫秒）。配合 Stagger 自动计算，也可手动指定。 */
  delay?: number;
  /** 渲染的标签，默认 div（表格场景可传 "tr"、Link 等）。 */
  as?: React.ElementType;
  className?: string;
  style?: React.CSSProperties;
  children?: React.ReactNode;
} & Record<string, unknown>;

/**
 * 内容入场：fade-in + 轻微上移（translate-y 4px→0），约 200ms。
 * 位移类动效在 prefers-reduced-motion 下由 globals.css 兜底降级为纯淡入。
 */
export const FadeIn = React.forwardRef<HTMLElement, FadeInProps>(
  ({ className, delay = 0, as, style, children, ...props }, ref) => {
    const Comp = (as ?? "div") as React.ElementType;
    const mergedStyle: React.CSSProperties = {
      ...(style as React.CSSProperties | undefined),
      animationDelay: delay ? `${delay}ms` : undefined,
    };
    return (
      <Comp
        ref={ref}
        className={cn("animate-fade-in-up", className as string | undefined)}
        style={mergedStyle}
        {...props}
      >
        {children}
      </Comp>
    );
  },
);
FadeIn.displayName = "FadeIn";

/** 计算第 index 项的错落延迟（带封顶）。供自定义场景（如 .map）使用。 */
export function staggerDelay(index: number): number {
  return Math.min(index, MAX_STAGGER_INDEX) * STEP_MS;
}

interface StaggerProps extends React.HTMLAttributes<HTMLDivElement> {
  /** 起始延迟（整组在某些区块后再开始时用）。 */
  startDelay?: number;
}

/**
 * 错落入场容器：把直接子元素逐项以递增延迟淡入。
 * 用 React.Children 注入 animation-delay，子元素需能接收 className/style
 * （建议子元素本身是 FadeIn 或普通带 animate 的元素）。
 *
 * 简化用法：直接给每个子元素套 animate-fade-in-up，并由本容器统一排期。
 */
export function Stagger({ children, startDelay = 0, className, ...props }: StaggerProps) {
  return (
    <div className={className} {...props}>
      {React.Children.map(children, (child, i) => {
        if (!React.isValidElement(child)) return child;
        const delay = startDelay + staggerDelay(i);
        const prev = (child.props as { style?: React.CSSProperties }).style ?? {};
        const prevClass = (child.props as { className?: string }).className ?? "";
        return React.cloneElement(child as React.ReactElement, {
          className: cn("animate-fade-in-up", prevClass),
          style: { animationDelay: `${delay}ms`, ...prev },
        });
      })}
    </div>
  );
}
