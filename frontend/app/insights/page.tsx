"use client";

import { AlertCircle, CheckCircle2, Download, FileText, Loader2, Settings, Trash2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogClose, DialogContent } from "@/components/ui/dialog";
import { Select } from "@/components/ui/select";
import { useT } from "@/lib/i18n/use-t";
import {
  downloadInsightDoc,
  useDeleteInsightDoc,
  useGenerateDaily,
  useInsightDocuments,
  useReportJob,
  type ReportJob,
} from "@/lib/hooks/use-insights";

const MARKETS = ["US", "CN", "HK", "JP"];

/** 阶段 → i18n key（用于"在生成什么"的提示）。 */
const STAGE_KEYS: Record<string, string> = {
  QUEUED: "insights.stage.queued",
  CONTEXT: "insights.stage.context",
  AI: "insights.stage.ai",
  SAVING: "insights.stage.saving",
  DONE: "insights.stage.done",
};

export default function InsightsPage() {
  const { t } = useT();
  const qc = useQueryClient();
  const [type, setType] = useState<string>("");
  const [page, setPage] = useState(1);
  const pageSize = 20;
  const { data, isLoading, isError, refetch } = useInsightDocuments(
    type || undefined,
    undefined,
    page,
    pageSize,
  );
  const generate = useGenerateDaily();
  const [genMarket, setGenMarket] = useState("US");

  // 当前正在跟踪的生成任务
  const [jobId, setJobId] = useState<number | null>(null);
  const { data: job } = useReportJob(jobId);

  // 删除确认
  const deleteDoc = useDeleteInsightDoc();
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  const docs = data?.data ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  // 任务完成/失败时：刷新列表并停止跟踪（保留一次成功提示由 job 状态驱动）
  const lastHandledRef = useRef<number | null>(null);
  useEffect(() => {
    if (!job) return;
    if ((job.status === "SUCCESS" || job.status === "FAILED") && lastHandledRef.current !== job.id) {
      lastHandledRef.current = job.id;
      if (job.status === "SUCCESS") {
        qc.invalidateQueries({ queryKey: ["insight-docs"] });
        qc.invalidateQueries({ queryKey: ["insight-unread"] });
      }
    }
  }, [job, qc]);

  const startGenerate = () => {
    generate.mutate(genMarket, {
      onSuccess: (j: ReportJob) => {
        lastHandledRef.current = null;
        setJobId(j.id);
      },
    });
  };

  const dismissJob = () => setJobId(null);

  const generating =
    generate.isPending ||
    (job != null && (job.status === "PENDING" || job.status === "RUNNING"));

  const confirmDelete = () => {
    const id = confirmDeleteId;
    if (id == null) return;
    setConfirmDeleteId(null);
    deleteDoc.mutate(id);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-display text-secondary">{t("insights.title")}</h1>
          <p className="mt-2 text-meta text-tertiary">{t("insights.subtitle")}</p>
        </div>
        <div className="flex items-center gap-2">
          <Select
            value={genMarket}
            onValueChange={setGenMarket}
            options={MARKETS.map((m) => ({ value: m, label: m }))}
            className="h-[34px] w-24"
          />
          <Button variant="secondary" disabled={generating} onClick={startGenerate}>
            {generating ? t("insights.generating") : t("insights.generate")}
          </Button>
          <Link href="/insights/config">
            <Button variant="outline">
              <Settings className="h-3.5 w-3.5" /> {t("insights.config")}
            </Button>
          </Link>
        </div>
      </div>

      {/* 生成任务进度卡（可感知的异步反馈） */}
      {job && (
        <JobProgress
          job={job}
          onDismiss={dismissJob}
          onRetry={startGenerate}
          stageLabel={(stage) => (STAGE_KEYS[stage] ? t(STAGE_KEYS[stage]) : stage)}
        />
      )}

      {/* 类型过滤 */}
      <div className="flex gap-2">
        {[
          { v: "", label: t("insights.all") },
          { v: "DAILY_REPORT", label: t("insights.typeDaily") },
          { v: "SCREENER_REVIEW", label: t("insights.typeScreener") },
        ].map((tab) => (
          <Button
            key={tab.v}
            size="sm"
            variant={type === tab.v ? "default" : "outline"}
            onClick={() => {
              setType(tab.v);
              setPage(1);
            }}
          >
            {tab.label}
          </Button>
        ))}
      </div>

      <Card className="overflow-hidden">
        {isLoading ? (
          [0, 1, 2].map((i) => (
            <div key={i} className="border-b border-border-default px-5 py-3">
              <div className="h-6 animate-pulse rounded bg-elevated" />
            </div>
          ))
        ) : isError ? (
          <div className="px-5 py-12 text-center">
            <AlertCircle className="mx-auto mb-3 h-8 w-8 text-down" />
            <div className="text-body text-secondary">{t("insights.loadError")}</div>
            <Button size="sm" variant="outline" className="mt-3" onClick={() => refetch()}>
              {t("insights.retry")}
            </Button>
          </div>
        ) : docs.length === 0 ? (
          <div className="px-5 py-12 text-center">
            <FileText className="mx-auto mb-3 h-8 w-8 text-tertiary" />
            <div className="text-body text-secondary">{t("insights.empty")}</div>
            <div className="mt-1 text-meta text-tertiary">{t("insights.emptyHint")}</div>
          </div>
        ) : (
          docs.map((d) => (
            <div
              key={d.id}
              className="flex items-center justify-between gap-3 border-b border-border-default px-5 py-3 last:border-b-0 hover:bg-elevated"
            >
              <Link href={`/insights/${d.id}`} className="flex min-w-0 flex-1 items-center gap-3">
                {!d.is_read && <span className="h-2 w-2 shrink-0 rounded-full bg-accent" />}
                <div className="min-w-0">
                  <div className="truncate text-body text-primary">{d.title}</div>
                  <div className="mt-0.5 flex items-center gap-2 text-caption text-tertiary">
                    <span className="rounded-badge border border-border-default px-1.5">
                      {d.doc_type === "DAILY_REPORT" ? t("insights.typeDaily") : t("insights.typeScreener")}
                    </span>
                    {d.market && <span>{d.market}</span>}
                    {d.degraded && <span className="text-warn">{t("insights.degraded")}</span>}
                    <span className="tnum">{(d.created_at ?? "").slice(0, 16).replace("T", " ")}</span>
                  </div>
                </div>
              </Link>
              <div className="flex shrink-0 items-center gap-1">
                <button
                  onClick={() => downloadInsightDoc(d.id)}
                  className="flex h-8 w-8 items-center justify-center rounded-md text-tertiary hover:bg-base hover:text-primary"
                  aria-label={t("insights.download")}
                  title={t("insights.download")}
                >
                  <Download className="h-4 w-4" />
                </button>
                <button
                  onClick={() => setConfirmDeleteId(d.id)}
                  className="flex h-8 w-8 items-center justify-center rounded-md text-tertiary hover:bg-base hover:text-down"
                  aria-label={t("insights.delete")}
                  title={t("insights.delete")}
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))
        )}
      </Card>

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3">
          <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            {t("insights.prev")}
          </Button>
          <span className="text-meta text-tertiary">{t("insights.page", { page })}</span>
          <Button size="sm" variant="outline" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
            {t("insights.next")}
          </Button>
        </div>
      )}

      {/* 删除确认弹窗 */}
      <Dialog open={confirmDeleteId != null} onOpenChange={(o) => !o && setConfirmDeleteId(null)}>
        <DialogContent title={t("insights.deleteTitle")} className="max-w-sm">
          <p className="text-body text-secondary">{t("insights.deleteConfirm")}</p>
          <div className="mt-5 flex justify-end gap-2">
            <DialogClose asChild>
              <Button variant="outline">{t("insights.cancel")}</Button>
            </DialogClose>
            <Button variant="danger" onClick={confirmDelete}>
              {t("insights.delete")}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

/** 生成任务进度卡：阶段说明 + 进度条 + 成功/失败态 + 重试。 */
function JobProgress({
  job,
  onDismiss,
  onRetry,
  stageLabel,
}: {
  job: ReportJob;
  onDismiss: () => void;
  onRetry: () => void;
  stageLabel: (stage: string) => string;
}) {
  const { t } = useT();
  const running = job.status === "PENDING" || job.status === "RUNNING";
  const failed = job.status === "FAILED";
  const success = job.status === "SUCCESS";

  return (
    <Card className="p-4">
      <div className="flex items-center gap-3">
        {running && <Loader2 className="h-4 w-4 shrink-0 animate-spin text-accent" />}
        {success && <CheckCircle2 className="h-4 w-4 shrink-0 text-up" />}
        {failed && <AlertCircle className="h-4 w-4 shrink-0 text-down" />}
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <span className="text-body font-medium text-primary">
              {job.market}{" · "}
              {running
                ? stageLabel(job.stage)
                : success
                  ? job.degraded
                    ? t("insights.jobDoneDegraded")
                    : t("insights.jobDone")
                  : t("insights.jobFailed")}
            </span>
            <span className="tnum text-caption text-tertiary">{job.progress}%</span>
          </div>
          {/* 进度条 */}
          <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-elevated">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                failed ? "bg-down" : success ? "bg-up" : "bg-accent"
              }`}
              style={{ width: `${Math.max(5, job.progress)}%` }}
            />
          </div>
          {job.message && (
            <p className={`mt-1.5 text-caption ${failed ? "text-down" : "text-tertiary"}`}>
              {job.message}
            </p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {success && job.document_id && (
            <Link href={`/insights/${job.document_id}`}>
              <Button size="sm" variant="secondary">{t("insights.viewDoc")}</Button>
            </Link>
          )}
          {failed && (
            <Button size="sm" variant="outline" onClick={onRetry}>
              {t("insights.retry")}
            </Button>
          )}
          {!running && (
            <Button size="sm" variant="ghost" onClick={onDismiss}>
              {t("insights.dismiss")}
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
}
