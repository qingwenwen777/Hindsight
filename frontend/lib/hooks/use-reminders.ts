"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";

export interface ReviewReminder {
  journal_id: number;
  stock_id: number;
  symbol: string;
  name: string;
  decision_type: string;
  decision_date: string;
  days_since: number;
  due_milestone: number;
  overdue_days: number;
}

export function useReviewReminders() {
  return useQuery({
    queryKey: ["review-reminders"],
    queryFn: async () =>
      (await api.get<ReviewReminder[]>("/reports/review-reminders")).data,
    refetchInterval: 60_000,
  });
}
