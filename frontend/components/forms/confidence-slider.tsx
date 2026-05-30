"use client";

import { useT } from "@/lib/i18n/use-t";
import { cn } from "@/lib/utils";

interface ConfidenceSliderProps {
  value?: number;
  onChange: (value: number) => void;
}

/**
 * 1-5 信心评分（设计文档 8.5 <ConfidenceSlider>）。
 * 点选式，1=很不确定 5=很确定。
 */
export function ConfidenceSlider({ value, onChange }: ConfidenceSliderProps) {
  const { t } = useT();
  return (
    <div className="flex items-center gap-2">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          onClick={() => onChange(n)}
          className={cn(
            "tnum flex h-9 w-9 items-center justify-center rounded-md border text-small transition-colors",
            value && n <= value
              ? "border-accent bg-accent/10 text-accent"
              : "border-border-subtle text-secondary hover:bg-elevated",
          )}
        >
          {n}
        </button>
      ))}
      <span className="ml-2 text-caption text-muted">
        {value ? t("form.confidenceScore", { n: value }) : t("form.notScored")}
      </span>
    </div>
  );
}
