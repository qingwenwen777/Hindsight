"use client";

import { useEffect, useState } from "react";

/**
 * 是否开启了系统「减弱动画」（prefers-reduced-motion: reduce）。
 * 用于 JS 驱动的动效（如数字滚动）做降级 —— CSS 动效已在 globals.css 兜底。
 * SSR 安全：首屏返回 false，挂载后再按真实值更新。
 */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const onChange = (e: MediaQueryListEvent) => setReduced(e.matches);
    mq.addEventListener?.("change", onChange);
    return () => mq.removeEventListener?.("change", onChange);
  }, []);

  return reduced;
}
