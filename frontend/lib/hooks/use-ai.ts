"use client";

import { useMutation, useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";

export interface AiBudget {
  monthly_budget_jpy: string;
  used_jpy: string;
  remaining_jpy: string;
  usage_ratio: number;
  is_close: boolean;
  available: boolean;
}

export interface ChatResponse {
  response: string;
  model: string;
  cached: boolean;
  degraded: boolean;
  cost_jpy: string | null;
  prompt_tokens: number;
  completion_tokens: number;
}

export interface ContextRef {
  type: "HOLDING" | "TRANSACTION" | "JOURNAL";
  id: number;
}

export function useAiBudget() {
  return useQuery({
    queryKey: ["ai-budget"],
    queryFn: async () => (await api.get<AiBudget>("/ai/budget")).data,
  });
}

export function useAiChat() {
  return useMutation({
    mutationFn: async (body: { message: string; context_refs: ContextRef[] }) =>
      (await api.post<ChatResponse>("/ai/chat", body)).data,
  });
}

export function useAiInsights() {
  return useQuery({
    queryKey: ["ai-insights"],
    queryFn: async () =>
      (
        await api.get<
          {
            id: number;
            prompt_type: string;
            model: string;
            cost_jpy: string | null;
            response: string;
            created_at: string | null;
          }[]
        >("/ai/insights")
      ).data,
  });
}
