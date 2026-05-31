"use client";

import { useEffect, useRef, useState } from "react";

export type FlashDir = "up" | "down" | null;

/**
 * 监听数值变化，返回本次变化方向（用于背景闪色）。
 * - 值变大 → "up"，变小 → "down"，约 440ms 后自动清空（与 flash 动画时长一致）。
 * - 首次挂载不闪。
 */
export function useFlashOnChange(value: number | null | undefined, durationMs = 440): FlashDir {
  const [dir, setDir] = useState<FlashDir>(null);
  const prevRef = useRef<number | null | undefined>(value);
  const mountedRef = useRef(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!mountedRef.current) {
      mountedRef.current = true;
      prevRef.current = value;
      return;
    }
    const prev = prevRef.current;
    prevRef.current = value;
    if (
      value == null ||
      prev == null ||
      !Number.isFinite(value) ||
      !Number.isFinite(prev) ||
      value === prev
    ) {
      return;
    }
    setDir(value > prev ? "up" : "down");
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setDir(null), durationMs);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [value, durationMs]);

  return dir;
}
