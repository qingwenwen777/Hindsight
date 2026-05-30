"use client";

import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { useT } from "@/lib/i18n/use-t";
import { cn } from "@/lib/utils";

interface CooldownButtonProps {
  /** 冷静期秒数（默认 30；复仇交易延长至 300） */
  seconds?: number;
  /** 倒计时结束并点击后触发 */
  onConfirm: () => void;
  disabled?: boolean;
  loading?: boolean;
  label?: string;
  className?: string;
}

/**
 * 冷静期提交按钮（设计文档 8.5 <CooldownButton>）。
 * 30 秒倒计时进度环，倒计时中文案"再想想，确定就提交"，可取消。
 * 倒计时结束后才允许真正提交。
 */
export function CooldownButton({
  seconds = 30,
  onConfirm,
  disabled = false,
  loading = false,
  label,
  className,
}: CooldownButtonProps) {
  const { t } = useT();
  const [counting, setCounting] = useState(false);
  const [remaining, setRemaining] = useState(seconds);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const start = () => {
    setCounting(true);
    setRemaining(seconds);
    timerRef.current = setInterval(() => {
      setRemaining((r) => {
        if (r <= 1) {
          if (timerRef.current) clearInterval(timerRef.current);
          return 0;
        }
        return r - 1;
      });
    }, 1000);
  };

  const cancel = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    setCounting(false);
    setRemaining(seconds);
  };

  const ready = counting && remaining === 0;
  const progress = ((seconds - remaining) / seconds) * 100;

  if (!counting) {
    return (
      <Button onClick={start} disabled={disabled || loading} className={className}>
        {label ?? t("form.confirmSubmit")}
      </Button>
    );
  }

  return (
    <div className="flex items-center gap-3">
      {ready ? (
        <Button onClick={onConfirm} disabled={loading} className={className}>
          {loading ? t("form.submitting") : t("form.confirmGo")}
        </Button>
      ) : (
        <div className="flex items-center gap-3">
          {/* 进度环 */}
          <div className="relative h-10 w-10">
            <svg className="h-10 w-10 -rotate-90" viewBox="0 0 36 36">
              <circle
                cx="18"
                cy="18"
                r="16"
                fill="none"
                className="stroke-border-subtle"
                strokeWidth="3"
              />
              <circle
                cx="18"
                cy="18"
                r="16"
                fill="none"
                className="stroke-accent"
                strokeWidth="3"
                strokeDasharray={`${(progress / 100) * 100.5} 100.5`}
                strokeLinecap="round"
              />
            </svg>
            <span className="tnum absolute inset-0 flex items-center justify-center text-small text-primary">
              {remaining}
            </span>
          </div>
          <span className="text-small text-secondary">{t("form.reconsider")}</span>
        </div>
      )}
      <Button variant="ghost" size="sm" onClick={cancel} disabled={loading}>
        {t("form.cancel")}
      </Button>
    </div>
  );
}
