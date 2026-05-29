"use client";

import {
  BarChart3,
  Bot,
  LayoutDashboard,
  LineChart,
  Settings,
  Star,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useUiStore } from "@/lib/store/ui-store";
import { cn } from "@/lib/utils";

/** 侧边导航项分组（文档 8.3：概览 / 交易 / 分析 / AI / 设置）。 */
const NAV_GROUPS: { title: string; items: { href: string; label: string; icon: typeof LayoutDashboard }[] }[] = [
  {
    title: "概览",
    items: [
      { href: "/", label: "仪表盘", icon: LayoutDashboard },
      { href: "/portfolio/holdings", label: "持仓", icon: Wallet },
      { href: "/watchlist", label: "关注", icon: Star },
    ],
  },
  {
    title: "交易",
    items: [
      { href: "/transactions", label: "交易记录", icon: LineChart },
      { href: "/journals", label: "决策日志", icon: BarChart3 },
    ],
  },
  {
    title: "分析",
    items: [
      { href: "/analytics/returns", label: "收益分析", icon: BarChart3 },
      { href: "/analytics/benchmark", label: "基准对比", icon: BarChart3 },
      { href: "/analytics/exposure", label: "暴露分析", icon: BarChart3 },
      { href: "/analytics/emotion", label: "情绪审计", icon: BarChart3 },
    ],
  },
  {
    title: "AI",
    items: [{ href: "/ai/chat", label: "AI 对话", icon: Bot }],
  },
  {
    title: "设置",
    items: [{ href: "/settings", label: "设置", icon: Settings }],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const collapsed = useUiStore((s) => s.sidebarCollapsed);
  const setCollapsed = useUiStore((s) => s.setSidebarCollapsed);

  return (
    <aside
      onMouseEnter={() => setCollapsed(false)}
      onMouseLeave={() => setCollapsed(true)}
      className={cn(
        "flex h-full flex-col border-r border-border-subtle bg-surface transition-all duration-200",
        collapsed ? "w-[56px]" : "w-[220px]",
      )}
    >
      <div className="flex h-14 items-center gap-2 px-4">
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-accent text-accent-foreground font-mono text-small font-semibold">
          T
        </div>
        {!collapsed && <span className="text-h2 text-primary">TradeAI</span>}
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-2">
        {NAV_GROUPS.map((group) => (
          <div key={group.title} className="mb-4">
            {!collapsed && (
              <div className="px-2 pb-1 text-caption uppercase tracking-wider text-muted">
                {group.title}
              </div>
            )}
            {group.items.map((item) => {
              const active = pathname === item.href;
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-2 py-2 text-small transition-colors",
                    active
                      ? "bg-elevated text-primary"
                      : "text-secondary hover:bg-elevated hover:text-primary",
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {!collapsed && <span className="truncate">{item.label}</span>}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
    </aside>
  );
}
