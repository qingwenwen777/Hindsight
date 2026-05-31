"use client";

import { ArrowUpCircle } from "lucide-react";

import { useT } from "@/lib/i18n/use-t";
import { useUpdaterStore } from "@/lib/hooks/use-updater";
import { cn } from "@/lib/utils";

/**
 * 品牌名右侧的更新标识。
 * 当有可用更新 / 下载中 / 下载完成时显示，点击重新打开更新弹窗。
 * 非桌面端或无更新时不渲染。
 */
export function UpdateBadge() {
  const { t } = useT();
  const isDesktop = useUpdaterStore((s) => s.isDesktop);
  const phase = useUpdaterStore((s) => s.phase);
  const percent = useUpdaterStore((s) => s.percent);
  const openDialog = useUpdaterStore((s) => s.openDialog);

  if (!isDesktop) return null;
  if (phase === "idle" || phase === "error") return null;

  return (
    <button
      type="button"
      onClick={openDialog}
      title={t("update.badge")}
      aria-label={t("update.badge")}
      className={cn(
        "inline-flex items-center gap-1 rounded-pill border px-1.5 py-0.5 text-[10px] font-medium transition-colors",
        "border-accent/40 bg-accent/10 text-accent hover:bg-accent/20",
      )}
    >
      <ArrowUpCircle className="h-3 w-3" />
      {phase === "downloading" ? <span className="tnum">{percent}%</span> : null}
      <span className={cn("h-1.5 w-1.5 rounded-full bg-accent", phase !== "downloading" && "animate-pulse")} />
    </button>
  );
}
