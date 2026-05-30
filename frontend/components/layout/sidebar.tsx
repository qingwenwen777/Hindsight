"use client";

import {
  Banknote,
  Bot,
  CandlestickChart,
  Heart,
  LayoutDashboard,
  type LucideIcon,
  NotebookPen,
  PanelLeftClose,
  PanelLeftOpen,
  PieChart,
  Receipt,
  Scale,
  Settings,
  Star,
  TrendingUp,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useUiStore } from "@/lib/store/ui-store";
import { cn } from "@/lib/utils";

const NAV_GROUPS: {
  title: string;
  items: { href: string; label: string; icon: LucideIcon }[];
}[] = [
  {
    title: "概览",
    items: [
      { href: "/", label: "仪表盘", icon: LayoutDashboard },
      { href: "/portfolio/holdings", label: "持仓", icon: Wallet },
      { href: "/portfolio/cash", label: "现金流", icon: Banknote },
      { href: "/watchlist", label: "关注", icon: Star },
    ],
  },
  {
    title: "交易",
    items: [
      { href: "/transactions", label: "交易记录", icon: Receipt },
      { href: "/journals", label: "决策日志", icon: NotebookPen },
    ],
  },
  {
    title: "分析",
    items: [
      { href: "/analytics/returns", label: "收益分析", icon: TrendingUp },
      { href: "/analytics/benchmark", label: "基准对比", icon: Scale },
      { href: "/analytics/exposure", label: "暴露分析", icon: PieChart },
      { href: "/analytics/emotion", label: "情绪审计", icon: Heart },
      { href: "/reports", label: "报表中心", icon: CandlestickChart },
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
      className={cn(
        "hidden shrink-0 flex-col border-r border-border-subtle bg-surface card-shadow transition-[width] duration-200 md:flex",
        collapsed ? "w-[56px]" : "w-[220px]",
      )}
    >
      {/* 品牌 — 纯文字，不要蓝色方块 */}
      <div className="flex h-[60px] items-center justify-between border-b border-border-subtle px-3">
        {!collapsed && (
          <span className="pl-2 text-title font-medium tracking-tight text-primary">
            Hindsight
          </span>
        )}
        {/* 手动折叠按钮 */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex h-8 w-8 items-center justify-center rounded-md text-tertiary hover:bg-elevated hover:text-primary"
          aria-label={collapsed ? "展开侧栏" : "收起侧栏"}
        >
          {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-3">
        {NAV_GROUPS.map((group) => (
          <div key={group.title} className="mb-4">
            {!collapsed && <div className="px-3 pb-1.5 label-caps">{group.title}</div>}
            <div className="grid gap-0.5">
              {group.items.map((item) => {
                const active =
                  item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    title={collapsed ? item.label : undefined}
                    className={cn(
                      "flex h-9 items-center gap-3 rounded-md px-3 text-body font-medium transition-colors",
                      active
                        ? "bg-elevated text-primary"
                        : "text-tertiary hover:bg-elevated hover:text-primary",
                      collapsed && "justify-center px-0",
                    )}
                  >
                    <Icon className="h-[18px] w-[18px] shrink-0" />
                    {!collapsed && <span className="truncate">{item.label}</span>}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>
    </aside>
  );
}
