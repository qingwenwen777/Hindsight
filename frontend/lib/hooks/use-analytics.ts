"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";

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
  return useQuery({
    queryKey: ["risk-metrics", days],
    queryFn: async () =>
      (await api.get<RiskMetrics>(`/portfolio/risk-metrics${days ? `?days=${days}` : ""}`)).data,
  });
}

export function useEquityCurve(days?: number) {
  return useQuery({
    queryKey: ["equity-curve", days],
    queryFn: async () =>
      (await api.get<EquityCurve>(`/portfolio/equity-curve${days ? `?days=${days}` : ""}`)).data,
  });
}

export function useReturns(type: "IRR" | "TWR") {
  return useQuery({
    queryKey: ["returns", type],
    queryFn: async () => (await api.get<any>(`/portfolio/returns?type=${type}`)).data,
  });
}
