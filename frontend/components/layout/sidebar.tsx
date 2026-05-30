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
    titleKey: "nav.group.ai",
    items: [{ href: "/ai/chat", labelKey: "nav.aiChat", icon: Bot }],
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
                const active =
                  item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
                const Icon = item.icon;
                const label = t(item.labelKey);
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
                    <Icon className="h-[18px] w-[18px] shrink-0" />
                    {!collapsed && <span className="truncate">{label}</span>}
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
