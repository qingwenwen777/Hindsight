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
  SlidersHorizontal,
  Star,
  TrendingUp,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { UpdateBadge } from "@/components/layout/update-badge";
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
      { href: "/insights/ai-config", labelKey: "nav.aiConfig", icon: SlidersHorizontal },
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
        "hidden shrink-0 flex-col border-r border-border-subtle bg-surface transition-[width] duration-200 md:flex",
        collapsed ? "w-[56px]" : "w-[228px]",
      )}
    >
      {/* 品牌 — 衬线感字标，告别居中小字 */}
      <div className="flex h-[60px] items-center justify-between border-b border-border-subtle px-4">
        {!collapsed && (
          <span className="flex items-center gap-2">
            <span className="text-[19px] font-semibold leading-none tracking-[-0.02em] text-primary">
              {t("brand.name")}
            </span>
            <UpdateBadge />
          </span>
        )}
        {/* 手动折叠按钮 */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex h-7 w-7 items-center justify-center rounded-md text-tertiary transition-colors hover:bg-elevated hover:text-primary"
          aria-label={collapsed ? t("sidebar.expand") : t("sidebar.collapse")}
        >
          {collapsed ? (
            <PanelLeftOpen className="h-4 w-4" strokeWidth={1.75} />
          ) : (
            <PanelLeftClose className="h-4 w-4" strokeWidth={1.75} />
          )}
        </button>
      </div>

      <nav className="no-scrollbar flex-1 overflow-y-auto px-2.5 py-4">
        {NAV_GROUPS.map((group, gi) => (
          <div
            key={group.titleKey}
            className={cn(
              gi > 0 && "mt-1.5 border-t border-border-subtle pt-3",
            )}
          >
            {!collapsed && (
              <div className="px-2.5 pb-1.5 pt-0.5 label-caps text-[10px] opacity-80">
                {t(group.titleKey)}
              </div>
            )}
            <div className="grid gap-px">
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
                      "group relative flex h-9 items-center gap-3 rounded-md px-2.5 text-body transition-colors duration-150",
                      active
                        ? "bg-elevated font-medium text-primary"
                        : "font-normal text-tertiary hover:bg-elevated/60 hover:text-secondary",
                      collapsed && "justify-center px-0",
                    )}
                  >
                    {/* active 指示条：用强调色建立产品身份与定位感 */}
                    {active && (
                      <span
                        className={cn(
                          "absolute left-0 top-1/2 h-4 w-[3px] -translate-y-1/2 rounded-r-full bg-accent",
                          collapsed && "left-0",
                        )}
                      />
                    )}
                    <span className="relative flex items-center">
                      <Icon
                        className={cn(
                          "h-[18px] w-[18px] shrink-0 transition-colors",
                          active ? "text-primary" : "text-tertiary group-hover:text-secondary",
                        )}
                        strokeWidth={active ? 2 : 1.75}
                      />
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
