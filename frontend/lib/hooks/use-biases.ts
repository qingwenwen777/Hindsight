"use client";

import { useMutation } from "@tanstack/react-query";

import { api } from "@/lib/api/client";

export interface CooldownCheckResult {
  cooldown_seconds: number;
  is_revenge: boolean;
  require_ai_confirm: boolean;
  warnings: string[];
  holding_time_warning?: {
    declared_horizon: string | null;
    held_days: number | null;
    reason: string;
  };
}

/** 录入前防御检测（复仇交易 / 持有时间）。 */
export function useCooldownCheck() {
  return useMutation({
    mutationFn: async (body: { stock_id: number; type: "BUY" | "SELL"; sell_date?: string }) =>
      (await api.post<CooldownCheckResult>("/biases/cooldown-check", body)).data,
  });
}
