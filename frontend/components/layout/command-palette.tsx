"use client";

import { Command } from "cmdk";
import {
  Bot,
  CandlestickChart,
  GitCompareArrows,
  Heart,
  LayoutDashboard,
  PieChart,
  PlusCircle,
  Search,
  Settings,
  Star,
  TrendingUp,
  Wallet,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api/client";
import type { Stock } from "@/lib/api/types";

interface NavCmd {
  label: string;
  href: string;
  icon: typeof LayoutDashboard;
}

const NAV_COMMANDS: NavCmd[] = [
  { label: "新建交易", href: "/transactions/new", icon: PlusCircle },
  { label: "仪表盘", href: "/", icon: LayoutDashboard },
  { label: "持仓", href: "/portfolio/holdings", icon: Wallet },
  { label: "关注列表", href: "/watchlist", icon: Star },
  { label: "交易记录", href: "/transactions", icon: CandlestickChart },
  { label: "收益分析", href: "/analytics/returns", icon: TrendingUp },
  { label: "基准对比", href: "/analytics/benchmark", icon: GitCompareArrows },
  { label: "暴露分析", href: "/analytics/exposure", icon: PieChart },
  { label: "情绪审计", href: "/analytics/emotion", icon: Heart },
  { label: "AI 对话", href: "/ai/chat", icon: Bot },
  { label: "设置", href: "/settings", icon: Settings },
];

/**
 * 全局命令面板（Cmd/Ctrl+K）。
 * 跳转页面、搜股票、新建交易。
 */
export function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [stocks, setStocks] = useState<Stock[]>([]);

  // Cmd/Ctrl+K 切换
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  // 股票搜索
  useEffect(() => {
    if (!open || query.trim().length === 0) {
      setStocks([]);
      return;
    }
    let cancelled = false;
    const t = setTimeout(async () => {
      try {
        const res = await api.get<Stock[]>(`/stocks/search?q=${encodeURIComponent(query)}`);
        if (!cancelled) setStocks(res.data.slice(0, 6));
      } catch {
        if (!cancelled) setStocks([]);
      }
    }, 200);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [query, open]);

  const go = (href: string) => {
    setOpen(false);
    setQuery("");
    router.push(href);
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 pt-[15vh]"
      onClick={() => setOpen(false)}
    >
      <Command
        className="w-full max-w-xl overflow-hidden rounded-lg border border-border-strong bg-elevated shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        shouldFilter={false}
      >
        <div className="flex items-center gap-2 border-b border-border-default px-4">
          <Search className="h-4 w-4 text-tertiary" />
          <Command.Input
            autoFocus
            value={query}
            onValueChange={setQuery}
            placeholder="跳转页面 / 搜索股票 / 新建交易…"
            className="h-12 w-full bg-transparent text-body text-primary outline-none placeholder:text-tertiary"
          />
          <kbd className="rounded border border-border-default px-1.5 py-0.5 text-caption text-tertiary">ESC</kbd>
        </div>
        <Command.List className="max-h-[360px] overflow-y-auto p-2">
          <Command.Empty className="px-3 py-6 text-center text-meta text-tertiary">
            无匹配项
          </Command.Empty>

          {stocks.length > 0 && (
            <Command.Group heading="股票" className="px-1 text-caption text-tertiary [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5">
              {stocks.map((s) => (
                <Command.Item
                  key={s.id}
                  value={`stock-${s.id}`}
                  onSelect={() => go(`/stocks/${s.id}`)}
                  className="flex cursor-pointer items-center justify-between rounded-md px-3 py-2 text-body text-secondary data-[selected=true]:bg-base data-[selected=true]:text-primary"
                >
                  <span>{s.name}</span>
                  <span className="tnum text-caption text-tertiary">{s.symbol} · {s.market}</span>
                </Command.Item>
              ))}
            </Command.Group>
          )}

          <Command.Group heading="导航" className="px-1 text-caption text-tertiary [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5">
            {NAV_COMMANDS.filter(
              (c) => query.trim() === "" || c.label.toLowerCase().includes(query.toLowerCase()),
            ).map((c) => {
              const Icon = c.icon;
              return (
                <Command.Item
                  key={c.href}
                  value={`nav-${c.href}`}
                  onSelect={() => go(c.href)}
                  className="flex cursor-pointer items-center gap-3 rounded-md px-3 py-2 text-body text-secondary data-[selected=true]:bg-base data-[selected=true]:text-primary"
                >
                  <Icon className="h-4 w-4" />
                  {c.label}
                </Command.Item>
              );
            })}
          </Command.Group>
        </Command.List>
      </Command>
    </div>
  );
}
