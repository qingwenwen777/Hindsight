"use client";

import { useEffect, useRef, useState } from "react";

import { useReducedMotion } from "@/lib/hooks/use-reduced-motion";

interface AnimatedNumberProps {
  /** 目标数值。 */
  value: number;
  /** 格式化函数：把当前插值格式化为展示字符串（货币/百分比等）。 */
  format: (n: number) => string;
  /** 动画时长（ms）。 */
  duration?: number;
  className?: string;
}

/** ease-out cubic：先快后慢，收尾稳。 */
function easeOut(t: number): number {
  return 1 - Math.pow(1 - t, 3);
}

/**
 * 数字滚动：值变化时用 requestAnimationFrame 从旧值平滑插值到新值（不引库）。
 * - 首次挂载直接显示目标值，不滚动（避免进场时所有数字一起爬升）。
 * - prefers-reduced-motion 下直接跳到目标值。
 */
export function AnimatedNumber({
  value,
  format,
  duration = 240,
  className,
}: AnimatedNumberProps) {
  const reduced = useReducedMotion();
  const [display, setDisplay] = useState(value);
  const fromRef = useRef(value);
  const rafRef = useRef<number | null>(null);
  const mountedRef = useRef(false);

  useEffect(() => {
    // 首次挂载：不滚动，直接落定
    if (!mountedRef.current) {
      mountedRef.current = true;
      fromRef.current = value;
      setDisplay(value);
      return;
    }
    if (reduced || !Number.isFinite(value)) {
      fromRef.current = value;
      setDisplay(value);
      return;
    }

    const from = fromRef.current;
    const to = value;
    if (from === to) return;

    const start = performance.now();
    if (rafRef.current) cancelAnimationFrame(rafRef.current);

    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const cur = from + (to - from) * easeOut(t);
      setDisplay(cur);
      if (t < 1) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        fromRef.current = to;
      }
    };
    rafRef.current = requestAnimationFrame(tick);

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [value, duration, reduced]);

  return <span className={className}>{format(display)}</span>;
}
