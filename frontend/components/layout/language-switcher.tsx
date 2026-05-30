"use client";

import { Languages } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { LOCALES } from "@/lib/i18n/messages";
import { useT } from "@/lib/i18n/use-t";
import { useUiStore, type Locale } from "@/lib/store/ui-store";
import { cn } from "@/lib/utils";

/** 顶栏语言切换（中 / 日 / EN）。 */
export function LanguageSwitcher() {
  const { t } = useT();
  const locale = useUiStore((s) => s.locale);
  const setLocale = useUiStore((s) => s.setLocale);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // 点击外部关闭
  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const current = LOCALES.find((l) => l.value === locale) ?? LOCALES[0];

  const pick = (l: Locale) => {
    setLocale(l);
    setOpen(false);
  };

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex h-[34px] items-center gap-1.5 rounded-md border border-border-default px-2.5 text-body font-medium text-secondary hover:border-border-strong hover:text-primary"
        aria-label={t("topbar.language")}
        title={t("topbar.language")}
      >
        <Languages className="h-4 w-4" />
        <span className="text-caption">{current.short}</span>
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-1 w-36 overflow-hidden rounded-md border border-border-strong bg-elevated p-1 shadow-xl">
          {LOCALES.map((l) => (
            <button
              key={l.value}
              onClick={() => pick(l.value)}
              className={cn(
                "flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-body outline-none transition-colors",
                l.value === locale
                  ? "bg-base text-primary"
                  : "text-secondary hover:bg-base hover:text-primary",
              )}
            >
              <span>{l.label}</span>
              <span className="text-caption text-tertiary">{l.short}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
