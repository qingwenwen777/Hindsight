"use client";

import { Download, Loader2, RefreshCw, RotateCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { useT } from "@/lib/i18n/use-t";
import { useUpdaterStore } from "@/lib/hooks/use-updater";

/** 自定义更新弹窗（适配 App UI，替代系统弹窗）。 */
export function UpdateDialog() {
  const { t } = useT();
  const {
    isDesktop,
    phase,
    version,
    notes,
    percent,
    errorMessage,
    dialogOpen,
    closeDialog,
    startDownload,
    install,
  } = useUpdaterStore();

  if (!isDesktop) return null;

  // 下载中不允许点遮罩关闭，避免误触；其它阶段可关（关掉后左上角仍有标识）
  const onOpenChange = (open: boolean) => {
    if (!open && phase !== "downloading") closeDialog();
  };

  const title =
    phase === "downloaded"
      ? t("update.downloadedTitle")
      : phase === "downloading"
        ? t("update.downloading")
        : phase === "error"
          ? t("update.errorTitle")
          : t("update.title");

  return (
    <Dialog open={dialogOpen} onOpenChange={onOpenChange}>
      <DialogContent title={title} className="max-w-md">
        {/* available：询问是否下载 */}
        {phase === "available" && (
          <div className="space-y-4">
            <p className="text-body text-secondary">
              {t("update.availableDesc", { version: version ?? "" })}
            </p>
            {notes && (
              <div className="rounded-md border border-border-default bg-elevated/40 p-3">
                <div className="label-caps mb-1.5">{t("update.notesTitle")}</div>
                <p className="whitespace-pre-wrap text-meta text-secondary">{notes}</p>
              </div>
            )}
            <div className="flex justify-end gap-2 pt-1">
              <Button variant="outline" onClick={closeDialog}>
                {t("update.later")}
              </Button>
              <Button onClick={startDownload}>
                <Download className="h-4 w-4" />
                {t("update.download")}
              </Button>
            </div>
          </div>
        )}

        {/* downloading：实时进度条 */}
        {phase === "downloading" && (
          <div className="space-y-4">
            <p className="text-meta text-tertiary">{t("update.downloadingDesc")}</p>
            <div className="space-y-1.5">
              <div className="h-2 w-full overflow-hidden rounded-full bg-elevated">
                <div
                  className="h-full rounded-full bg-accent transition-[width] duration-200 ease-out"
                  style={{ width: `${Math.max(3, percent)}%` }}
                />
              </div>
              <div className="flex items-center justify-between text-caption text-tertiary">
                <span className="inline-flex items-center gap-1.5">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  {t("update.downloading")}
                </span>
                <span className="tnum">{percent}%</span>
              </div>
            </div>
          </div>
        )}

        {/* downloaded：重启安装 */}
        {phase === "downloaded" && (
          <div className="space-y-4">
            <p className="text-body text-secondary">
              {t("update.downloadedDesc", { version: version ?? "" })}
            </p>
            <div className="flex justify-end gap-2 pt-1">
              <Button variant="outline" onClick={closeDialog}>
                {t("update.later")}
              </Button>
              <Button onClick={install}>
                <RotateCw className="h-4 w-4" />
                {t("update.restartNow")}
              </Button>
            </div>
          </div>
        )}

        {/* error */}
        {phase === "error" && (
          <div className="space-y-4">
            <p className="text-body text-down">{errorMessage}</p>
            <div className="flex justify-end gap-2 pt-1">
              <Button variant="outline" onClick={closeDialog}>
                {t("update.close")}
              </Button>
              <Button onClick={startDownload}>
                <RefreshCw className="h-4 w-4" />
                {t("update.retry")}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
