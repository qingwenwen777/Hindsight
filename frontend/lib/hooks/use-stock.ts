"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import type { Stock, Transaction } from "@/lib/api/types";

export interface PriceBar {
  date: string;
  open: string | null;
  high: string | null;
  low: string | null;
  close: string | null;
  volume: number | null;
}

export interface IndicatorData {
  dates: string[];
  indicators: {
    ma?: Record<string, (number | null)[]>;
    ema?: Record<string, (number | null)[]>;
    macd?: { dif: (number | null)[]; dea: (number | null)[]; hist: (number | null)[] };
    rsi?: Record<string, (number | null)[]>;
    boll?: { mid: (number | null)[]; upper: (number | null)[]; lower: (number | null)[] };
    kdj?: { k: (number | null)[]; d: (number | null)[]; j: (number | null)[] };
  };
}

export function useStock(id: number) {
  return useQuery({
    queryKey: ["stock", id],
    queryFn: async () => (await api.get<Stock>(`/stocks/${id}`)).data,
    enabled: Number.isFinite(id),
  });
}

export function usePrices(id: number) {
  return useQuery({
    queryKey: ["prices", id],
    queryFn: async () => (await api.get<PriceBar[]>(`/stocks/${id}/prices`)).data,
    enabled: Number.isFinite(id),
  });
}

export function useIndicators(id: number, types = "MA,BOLL,MACD,RSI") {
  return useQuery({
    queryKey: ["indicators", id, types],
    queryFn: async () =>
      (await api.get<IndicatorData>(`/stocks/${id}/indicators?type=${types}`)).data,
    enabled: Number.isFinite(id),
  });
}

export function useStockTransactions(id: number) {
  return useQuery({
    queryKey: ["stock-transactions", id],
    queryFn: async () =>
      (await api.get<Transaction[]>(`/transactions?stock_id=${id}`)).data,
    enabled: Number.isFinite(id),
  });
}
