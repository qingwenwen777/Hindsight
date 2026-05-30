"use client";

import { useCallback } from "react";

import { useUiStore } from "@/lib/store/ui-store";
import { MESSAGES, type Locale } from "@/lib/i18n/messages";

/** 翻译函数类型：t(key, vars?) -> string */
export type TFunc = (key: string, vars?: Record<string, string | number>) => string;

function interpolate(template: string, vars?: Record<string, string | number>): string {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (_, k) =>
    vars[k] !== undefined ? String(vars[k]) : `{${k}}`,
  );
}

/**
 * 取当前语言的翻译函数。缺失 key 回退中文，再回退 key 本身。
 */
export function useT(): { t: TFunc; locale: Locale } {
  const locale = useUiStore((s) => s.locale);

  const t = useCallback<TFunc>(
    (key, vars) => {
      const dict = MESSAGES[locale] ?? MESSAGES.zh;
      const raw = dict[key] ?? MESSAGES.zh[key] ?? key;
      return interpolate(raw, vars);
    },
    [locale],
  );

  return { t, locale };
}
