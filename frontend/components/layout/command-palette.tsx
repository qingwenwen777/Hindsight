"use client";

import { Command } from "cmdk";
import {
  Bot,
  CandlestickChart,
  GitCompareArrows,
  Heart,
  LayoutDashboard,
  PieChart,
  Plus,
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
import type { DiscoverCandidate, Stock } from "@/lib/api/types";
import { useT } from "@/lib/i18n/use-t";

interface NavCmd {
  labelKey: string;
  href: string;
  icon: typeof LayoutDashboard;
}

const NAV_COMMANDS: NavCmd[] = [
  { labelKey: "nav.newTransaction", href: "/transactions/new", icon: PlusCircle },
  { labelKey: "nav.dashboard", href: "/", icon: LayoutDashboard },
  { labelKey: "nav.holdings", href: "/portfolio/holdings", icon: Wallet },
  { labelKey: "nav.watchlist", href: "/watchlist", icon: Star },
  { labelKey: "nav.transactions", href: "/transactions", icon: CandlestickChart },
  { labelKey: "nav.returns", href: "/analytics/returns", icon: TrendingUp },
  { labelKey: "nav.benchmark", href: "/analytics/benchmark", icon: GitCompareArrows },
  { labelKey: "nav.exposure", href: "/analytics/exposure", icon: PieChart },
  { labelKey: "nav.emotion", href: "/analytics/emotion", icon: Heart },
  { labelKey: "nav.aiChat", href: "/ai/chat", icon: Bot },
  { labelKey: "nav.settings", href: "/settings", icon: Settings },
];

/**
 * 全局命令面板（Cmd/Ctrl+K）。
 * 跳转页面、搜股票、新建交易。
 */
export function CommandPalette() {
  const router = useRouter();
  const { t } = useT();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [discovered, setDiscovered] = useState<DiscoverCandidate[]>([]);
  const [adding, setAdding] = useState<string | null>(null);

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

  // 股票搜索（本地库；查不到再从数据源发现）
  useEffect(() => {
    if (!open || query.trim().length === 0) {
      setStocks([]);
      setDiscovered([]);
      return;
    }
    let cancelled = false;
    const t = setTimeout(async () => {
      try {
        const res = await api.get<Stock[]>(`/stocks/search?q=${encodeURIComponent(query)}`);
        if (cancelled) return;
        const local = res.data.slice(0, 6);
        setStocks(local);
        if (local.length === 0 && query.trim().length >= 2) {
          try {
            const dis = await api.get<DiscoverCandidate[]>(
              `/stocks/discover?q=${encodeURIComponent(query)}`,
            );
            if (!cancelled) setDiscovered(dis.data.slice(0, 6));
          } catch {
            if (!cancelled) setDiscovered([]);
          }
        } else {
          setDiscovered([]);
        }
      } catch {
        if (!cancelled) {
          setStocks([]);
          setDiscovered([]);
        }
      }
    }, 250);
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

  // 一键登记候选股票（含后台同步行情）并跳转个股页
  const addAndGo = async (c: DiscoverCandidate) => {
    const key = `${c.market}:${c.symbol}`;
    setAdding(key);
    try {
      const res = await api.post<Stock>("/stocks", {
        symbol: c.symbol,
        market: c.market,
        name: c.name,
        currency: c.currency,
        is_etf: c.quote_type === "ETF",
        sync: true,
      });
      go(`/stocks/${res.data.id}`);
    } catch {
      setAdding(null);
    }
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
            placeholder={t("cmd.placeholder")}
            className="h-12 w-full bg-transparent text-body text-primary outline-none placeholder:text-tertiary"
          />
          <kbd className="rounded border border-border-default px-1.5 py-0.5 text-caption text-tertiary">ESC</kbd>
        </div>
        <Command.List className="max-h-[360px] overflow-y-auto p-2">
          <Command.Empty className="px-3 py-6 text-center text-meta text-tertiary">
            {t("cmd.noMatch")}
          </Command.Empty>

          {stocks.length > 0 && (
            <Command.Group heading={t("cmd.stocks")} className="px-1 text-caption text-tertiary [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5">
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

          {stocks.length === 0 && discovered.length > 0 && (
            <Command.Group heading={t("cmd.discoverGroup")} className="px-1 text-caption text-tertiary [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5">
              {discovered.map((c) => {
                const key = `${c.market}:${c.symbol}`;
                return (
                  <Command.Item
                    key={key}
                    value={`discover-${key}`}
                    onSelect={() => addAndGo(c)}
                    className="flex cursor-pointer items-center justify-between rounded-md px-3 py-2 text-body text-secondary data-[selected=true]:bg-base data-[selected=true]:text-primary"
                  >
                    <span className="flex items-center gap-2">
                      <Plus className="h-3.5 w-3.5 text-accent" />
                      {c.name}
                    </span>
                    <span className="tnum text-caption text-tertiary">
                      {adding === key ? t("cmd.adding") : `${c.symbol} · ${c.market}`}
                    </span>
                  </Command.Item>
                );
              })}
            </Command.Group>
          )}

          <Command.Group heading={t("cmd.nav")} className="px-1 text-caption text-tertiary [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5">
            {NAV_COMMANDS.filter(
              (c) => query.trim() === "" || t(c.labelKey).toLowerCase().includes(query.toLowerCase()),
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
                  {t(c.labelKey)}
                </Command.Item>
              );
            })}
          </Command.Group>
        </Command.List>
      </Command>
    </div>
  );
}
