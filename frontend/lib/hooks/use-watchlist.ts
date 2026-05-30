"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";

export interface WatchItem {
  id: number;
  stock_id: number;
  symbol: string;
  market: string;
  name: string;
  currency: string;
  last_price: string | null;
  notes: string | null;
  tags: string[] | null;
  added_at: string | null;
}

export function useWatchlist() {
  return useQuery({
    queryKey: ["watchlist"],
    queryFn: async () => (await api.get<WatchItem[]>("/watchlist")).data,
  });
}

export function useAddWatch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { stock_id: number; tags?: string[]; notes?: string }) =>
      (await api.post<{ id: number; already: boolean }>("/watchlist", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlist"] }),
  });
}

export function useRemoveWatch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (stockId: number) =>
      (await api.delete<{ removed: number }>(`/watchlist/${stockId}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlist"] }),
  });
}
