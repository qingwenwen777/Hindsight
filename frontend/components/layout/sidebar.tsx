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
  ScanSearch,
  Settings,
  Star,
  TrendingUp,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useInsightUnread } from "@/lib/hooks/use-insights";
import { useT } from "@/lib/i18n/use-t";
import { useUiStore } from "@/lib/store/ui-store";
import { cn } from "@/lib/utils";

const NAV_GROUPS: {
  titleKey: string;
  items: { href: string; labelKey: string; icon: LucideIcon }[];
}[] = [
  {
    titleKey: "nav.group.overview",
    items: [
      { href: "/", labelKey: "nav.dashboard", icon: LayoutDashboard },
      { href: "/portfolio/holdings", labelKey: "nav.holdings", icon: Wallet },
      { href: "/portfolio/cash", labelKey: "nav.cash", icon: Banknote },
      { href: "/watchlist", labelKey: "nav.watchlist", icon: Star },
    ],
  },
  {
    titleKey: "nav.group.trading",
    items: [
      { href: "/transactions", labelKey: "nav.transactions", icon: Receipt },
      { href: "/journals", labelKey: "nav.journals", icon: NotebookPen },
    ],
  },
  {
    titleKey: "nav.group.analysis",
    items: [
      { href: "/analytics/returns", labelKey: "nav.returns", icon: TrendingUp },
      { href: "/analytics/benchmark", labelKey: "nav.benchmark", icon: Scale },
      { href: "/analytics/exposure", labelKey: "nav.exposure", icon: PieChart },
      { href: "/analytics/emotion", labelKey: "nav.emotion", icon: Heart },
      { href: "/reports", labelKey: "nav.reports", icon: CandlestickChart },
    ],
  },
  {
    titleKey: "nav.group.insights",
    items: [
      { href: "/insights", labelKey: "nav.insightsReports", icon: CandlestickChart },
      { href: "/insights/screener", labelKey: "nav.screener", icon: ScanSearch },
      { href: "/ai/chat", labelKey: "nav.aiChat", icon: Bot },
    ],
  },
  {
    titleKey: "nav.group.settings",
    items: [{ href: "/settings", labelKey: "nav.settings", icon: Settings }],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { t } = useT();
  const collapsed = useUiStore((s) => s.sidebarCollapsed);
  const setCollapsed = useUiStore((s) => s.setSidebarCollapsed);
  const { data: insightUnread } = useInsightUnread();

  // 找出与当前路径最匹配的导航项（最长前缀），避免父子路径同时高亮
  // 例：/insights/screener 应只高亮"选股筛选"，不高亮"AI 日报"(/insights)
  const allHrefs = NAV_GROUPS.flatMap((g) => g.items.map((i) => i.href));
  const activeHref = allHrefs.reduce((best, href) => {
    const match = href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(href + "/");
    if (!match) return best;
    return href.length > best.length ? href : best;
  }, "");

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
            {t("brand.name")}
          </span>
        )}
        {/* 手动折叠按钮 */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex h-8 w-8 items-center justify-center rounded-md text-tertiary hover:bg-elevated hover:text-primary"
          aria-label={collapsed ? t("sidebar.expand") : t("sidebar.collapse")}
        >
          {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-3">
        {NAV_GROUPS.map((group) => (
          <div key={group.titleKey} className="mb-4">
            {!collapsed && <div className="px-3 pb-1.5 label-caps">{t(group.titleKey)}</div>}
            <div className="grid gap-0.5">
              {group.items.map((item) => {
                const active = item.href === activeHref;
                const Icon = item.icon;
                const label = t(item.labelKey);
                const showDot = item.href === "/insights" && (insightUnread ?? 0) > 0;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    title={collapsed ? label : undefined}
                    className={cn(
                      "flex h-9 items-center gap-3 rounded-md px-3 text-body font-medium transition-colors",
                      active
                        ? "bg-elevated text-primary"
                        : "text-tertiary hover:bg-elevated hover:text-primary",
                      collapsed && "justify-center px-0",
                    )}
                  >
                    <span className="relative flex items-center">
                      <Icon className="h-[18px] w-[18px] shrink-0" />
                      {showDot && (
                        <span className="absolute -right-1 -top-1 h-2 w-2 rounded-full bg-accent" />
                      )}
                    </span>
                    {!collapsed && <span className="truncate">{label}</span>}
                    {!collapsed && showDot && (
                      <span className="ml-auto h-1.5 w-1.5 rounded-full bg-accent" />
                    )}
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
