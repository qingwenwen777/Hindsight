"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";

export interface PriceAlert {
  id: number;
  stock_id: number;
  journal_id: number | null;
  symbol: string;
  name: string;
  alert_type: "TARGET" | "STOP";
  threshold: string;
  triggered_price: string;
  is_read: boolean;
  triggered_at: string | null;
}

export function usePriceAlerts() {
  return useQuery({
    queryKey: ["price-alerts"],
    queryFn: async () => (await api.get<PriceAlert[]>("/alerts/price")).data,
    refetchInterval: 60_000,
  });
}

export function useMarkAlertRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => (await api.post(`/alerts/price/${id}/read`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["price-alerts"] }),
  });
}

export function useMarkAllAlertsRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => (await api.post(`/alerts/price/read-all`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["price-alerts"] }),
  });
}
