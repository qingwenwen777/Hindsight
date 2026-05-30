"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";

export interface ScreenCondition {
  field: string;
  op: string;
  value?: string | number | boolean | null;
  value2?: string | number | null;
}

export interface ScreenHit {
  stock_id: number;
  symbol: string;
  name: string;
  market: string;
  matched: Record<string, string>;
  missing: string[];
}

export interface ScreenerRule {
  id: number;
  name: string;
  conditions: ScreenCondition[];
  markets: string[] | null;
  updated_at: string | null;
}

export function useScreenerFields() {
  return useQuery({
    queryKey: ["screener-fields"],
    queryFn: async () =>
      (await api.get<{ fields: string[]; operators: string[] }>("/screener/fields")).data,
    staleTime: Infinity,
  });
}

export function useScreenerRules() {
  return useQuery({
    queryKey: ["screener-rules"],
    queryFn: async () => (await api.get<ScreenerRule[]>("/screener/rules")).data,
  });
}

export function useRunScreen() {
  return useMutation({
    mutationFn: async (body: { conditions: ScreenCondition[]; markets?: string[] | null }) =>
      (await api.post<ScreenHit[]>("/screener/run", body)).data,
  });
}

export function useSaveRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { name: string; conditions: ScreenCondition[]; markets?: string[] | null }) =>
      (await api.post<{ id: number }>("/screener/rules", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["screener-rules"] }),
  });
}

export function useDeleteRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => (await api.delete(`/screener/rules/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["screener-rules"] }),
  });
}

export function useReviewScreen() {
  return useMutation({
    mutationFn: async (body: {
      conditions?: ScreenCondition[];
      markets?: string[] | null;
      rule_id?: number;
      rule_name?: string;
      language?: string;
    }) => (await api.post("/screener/review", body)).data,
  });
}
