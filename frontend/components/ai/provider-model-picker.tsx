"use client";

import { Check, ChevronDown, Cpu } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { useAiProviders } from "@/lib/hooks/use-ai-providers";
import { useT } from "@/lib/i18n/use-t";
import { cn } from "@/lib/utils";

interface Props {
  providerId: number | null;
  model: string | null;
  /** 传 (providerId, model)。providerId=null 表示用全局默认服务商。 */
  onChange: (providerId: number | null, model: string | null) => void;
  /** 是否提供"使用默认"选项（日报配置里用）。 */
  allowDefault?: boolean;
}

/** 服务商 + 模型选择器。对话顶部用作临时切换；日报配置里用作固定选择。 */
export function ProviderModelPicker({ providerId, model, onChange, allowDefault = true }: Props) {
  const { t } = useT();
  const { data: providers } = useAiProviders();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const enabled = (providers ?? []).filter((p) => p.enabled);
  const defaultProvider = enabled.find((p) => p.is_default) ?? enabled[0];

  // 当前显示标签
  let label = t("ai.providerDefault");
  if (providerId != null) {
    const p = enabled.find((x) => x.id === providerId);
    if (p) label = model ? `${p.name} · ${model}` : p.name;
  } else if (model && defaultProvider) {
    label = `${defaultProvider.name} · ${model}`;
  } else if (defaultProvider) {
    label = defaultProvider.default_model
      ? `${defaultProvider.name} · ${defaultProvider.default_model}`
      : defaultProvider.name;
  }

  if (enabled.length === 0) {
    return (
      <Link
        href="/insights/ai-config"
        className="inline-flex items-center gap-1.5 rounded-lg border border-border-default px-2.5 py-1.5 text-caption text-tertiary hover:text-primary"
      >
        <Cpu className="h-3.5 w-3.5" />
        {t("ai.noProvider")}
      </Link>
    );
  }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="inline-flex max-w-[220px] items-center gap-1.5 rounded-lg border border-border-default px-2.5 py-1.5 text-caption text-secondary hover:border-border-strong hover:text-primary"
      >
        <Cpu className="h-3.5 w-3.5 shrink-0" />
        <span className="truncate">{label}</span>
        <ChevronDown className="h-3.5 w-3.5 shrink-0 text-tertiary" />
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-1 max-h-80 w-64 overflow-y-auto rounded-lg border border-border-strong bg-elevated p-1 shadow-xl">
          {allowDefault && (
            <button
              onClick={() => {
                onChange(null, null);
                setOpen(false);
              }}
              className={cn(
                "flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-body transition-colors hover:bg-base hover:text-primary",
                providerId == null ? "text-primary" : "text-secondary",
              )}
            >
              <span>{t("ai.providerDefault")}</span>
              {providerId == null && <Check className="h-3.5 w-3.5" />}
            </button>
          )}
          {enabled.map((p) => (
            <div key={p.id} className="px-1 py-1">
              <div className="px-2 pb-1 label-caps">{p.name}</div>
              {(p.models.length > 0 ? p.models : p.default_model ? [p.default_model] : []).map((m) => {
                const isActive = providerId === p.id && model === m;
                return (
                  <button
                    key={m}
                    onClick={() => {
                      onChange(p.id, m);
                      setOpen(false);
                    }}
                    className={cn(
                      "flex w-full items-center justify-between rounded-md px-3 py-1.5 text-left text-body transition-colors hover:bg-base hover:text-primary",
                      isActive ? "text-primary" : "text-secondary",
                    )}
                  >
                    <span className="truncate">{m}</span>
                    {isActive && <Check className="h-3.5 w-3.5 shrink-0" />}
                  </button>
                );
              })}
              {p.models.length === 0 && !p.default_model && (
                <p className="px-3 py-1 text-caption text-tertiary">—</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
