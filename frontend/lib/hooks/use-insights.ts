"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";

export interface InsightDocBrief {
  id: number;
  doc_type: string;
  market: string | null;
  title: string;
  report_date: string | null;
  degraded: boolean;
  is_read: boolean;
  model: string | null;
  created_at: string | null;
}

export interface InsightDocDetail extends InsightDocBrief {
  body_md: string;
  degraded_reason: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  source_ref: Record<string, unknown> | null;
}

export interface ReportConfig {
  enabled_markets: string[];
  schedule: Record<string, string>;
  move_threshold_pct: string;
  detail_level: string;
  tone: string;
  language: string;
  focus_text: string | null;
  constraints: string[];
  provider_id: number | null;
  model_name: string | null;
  updated_at: string | null;
}

export interface ReportJob {
  id: number;
  market: string;
  status: "PENDING" | "RUNNING" | "SUCCESS" | "FAILED";
  stage: string;
  progress: number;
  message: string | null;
  document_id: number | null;
  degraded: boolean;
  created_at: string | null;
  updated_at: string | null;
  finished_at: string | null;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useInsightDocuments(type?: string, market?: string, page = 1, pageSize = 20) {
  const params = new URLSearchParams();
  if (type) params.set("type", type);
  if (market) params.set("market", market);
  params.set("page", String(page));
  params.set("page_size", String(pageSize));
  return useQuery({
    queryKey: ["insight-docs", type ?? "", market ?? "", page, pageSize],
    queryFn: async () => {
      const res = await api.get<InsightDocBrief[]>(`/insights/documents?${params.toString()}`);
      return { data: res.data, total: res.meta?.total ?? res.data.length };
    },
  });
}

export function useInsightDoc(id: number) {
  return useQuery({
    queryKey: ["insight-doc", id],
    queryFn: async () => (await api.get<InsightDocDetail>(`/insights/documents/${id}`)).data,
    enabled: Number.isFinite(id),
  });
}

export function useInsightUnread() {
  return useQuery({
    queryKey: ["insight-unread"],
    queryFn: async () => (await api.get<{ count: number }>("/insights/unread-count")).data.count,
    refetchInterval: 60_000,
  });
}

export function useMarkInsightRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => (await api.post(`/insights/documents/${id}/read`)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["insight-docs"] });
      qc.invalidateQueries({ queryKey: ["insight-unread"] });
    },
  });
}

/** 启动日报生成任务（异步），返回任务对象供轮询。 */
export function useGenerateDaily() {
  return useMutation({
    mutationFn: async (market: string) =>
      (await api.post<ReportJob>(`/insights/daily/generate?market=${market}`)).data,
  });
}

/** 轮询单个日报生成任务状态，直到完成/失败。 */
export function useReportJob(jobId: number | null) {
  return useQuery({
    queryKey: ["report-job", jobId],
    queryFn: async () => (await api.get<ReportJob>(`/insights/daily/jobs/${jobId}`)).data,
    enabled: jobId != null,
    // 任务进行中每 1.5s 轮询一次；完成/失败后停止
    refetchInterval: (query) => {
      const data = query.state.data as ReportJob | undefined;
      if (!data) return 1500;
      return data.status === "SUCCESS" || data.status === "FAILED" ? false : 1500;
    },
  });
}

/** 删除一篇洞察文档。 */
export function useDeleteInsightDoc() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => (await api.delete(`/insights/documents/${id}`)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["insight-docs"] });
      qc.invalidateQueries({ queryKey: ["insight-unread"] });
    },
  });
}

export function useReportConfig() {
  return useQuery({
    queryKey: ["report-config"],
    queryFn: async () => (await api.get<ReportConfig>("/insights/config")).data,
  });
}

export function useSaveReportConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<ReportConfig>) =>
      (await api.put<ReportConfig>("/insights/config", payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["report-config"] }),
  });
}

/** 下载文档为 .md */
export function downloadInsightDoc(id: number) {
  window.open(`${API_BASE}/api/v1/insights/documents/${id}/download`, "_blank");
}
