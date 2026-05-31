"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { useUiStore } from "@/lib/store/ui-store";

export interface RiskMetrics {
  available: boolean;
  message?: string;
  total_return_pct?: number;
  annualized_return_pct?: number;
  annualized_volatility_pct?: number;
  max_drawdown_pct?: number;
  sharpe?: number;
  calmar?: number;
  samples?: number;
  drawdown_series?: { date: string; drawdown_pct: number }[];
}

export interface EquityCurve {
  dates: string[];
  equity: number[];
  normalized: number[];
}

export function useRiskMetrics(days?: number) {
  const currency = useUiStore((s) => s.baseCurrency);
  return useQuery({
    queryKey: ["risk-metrics", days, currency],
    queryFn: async () => {
      const params = new URLSearchParams({ currency });
      if (days) params.set("days", String(days));
      return (await api.get<RiskMetrics>(`/portfolio/risk-metrics?${params}`)).data;
    },
  });
}

export function useEquityCurve(days?: number) {
  const currency = useUiStore((s) => s.baseCurrency);
  return useQuery({
    queryKey: ["equity-curve", days, currency],
    queryFn: async () => {
      const params = new URLSearchParams({ currency });
      if (days) params.set("days", String(days));
      return (await api.get<EquityCurve>(`/portfolio/equity-curve?${params}`)).data;
    },
  });
}

export function useReturns(type: "IRR" | "TWR") {
  const currency = useUiStore((s) => s.baseCurrency);
  return useQuery({
    queryKey: ["returns", type, currency],
    queryFn: async () =>
      (await api.get<any>(`/portfolio/returns?type=${type}&currency=${currency}`)).data,
  });
}
