"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import type { Review } from "@/lib/api/types";

/** 复盘录入入参（对应后端 ReviewCreate）。 */
export interface ReviewCreate {
  review_date?: string;
  days_since_decision?: number;
  price_at_review?: string;
  pnl_pct?: string;
  benchmark_pnl_pct?: string;
  thesis_held?: boolean | null;
  luck_vs_skill?: string | null;
  lessons?: string;
  notes?: string;
}

/** 某日志的复盘列表 */
export function useReviews(journalId: number) {
  return useQuery({
    queryKey: ["reviews", journalId],
    queryFn: async () => (await api.get<Review[]>(`/journals/${journalId}/reviews`)).data,
    enabled: Number.isFinite(journalId),
  });
}

/** 追加复盘 */
export function useAddReview(journalId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ReviewCreate) =>
      (await api.post<Review>(`/journals/${journalId}/reviews`, payload)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["reviews", journalId] });
      qc.invalidateQueries({ queryKey: ["review-reminders"] });
    },
  });
}
