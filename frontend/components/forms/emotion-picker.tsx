"use client";

import { cn } from "@/lib/utils";

/** 情绪选项（设计文档 8.5 <EmotionPicker>）。 */
export const EMOTIONS = [
  { value: "CALM", emoji: "😐", label: "冷静" },
  { value: "HESITANT", emoji: "🤔", label: "犹豫" },
  { value: "FOMO", emoji: "🤩", label: "FOMO" },
  { value: "PANIC", emoji: "😱", label: "恐慌" },
  { value: "REVENGE", emoji: "😤", label: "复仇" },
] as const;

interface EmotionPickerProps {
  value?: string;
  onChange: (value: string) => void;
}

export function EmotionPicker({ value, onChange }: EmotionPickerProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {EMOTIONS.map((e) => (
        <button
          key={e.value}
          type="button"
          onClick={() => onChange(e.value)}
          className={cn(
            "flex flex-col items-center gap-1 rounded-md border px-3 py-2 transition-colors",
            value === e.value
              ? "border-accent bg-accent/10 text-primary"
              : "border-border-subtle text-secondary hover:bg-elevated",
          )}
        >
          <span className="text-lg">{e.emoji}</span>
          <span className="text-caption">{e.label}</span>
        </button>
      ))}
    </div>
  );
}
