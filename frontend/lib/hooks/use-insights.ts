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

export function useGenerateDaily() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (market: string) =>
      (await api.post(`/insights/daily/generate?market=${market}`)).data,
    onSuccess: () => {
      setTimeout(() => qc.invalidateQueries({ queryKey: ["insight-docs"] }), 4000);
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
