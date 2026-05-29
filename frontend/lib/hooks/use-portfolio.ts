"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import type {
  Holding,
  Journal,
  PortfolioSummary,
  Stock,
  Transaction,
  TransactionCreate,
} from "@/lib/api/types";

/** 持仓列表 */
export function useHoldings() {
  return useQuery({
    queryKey: ["holdings"],
    queryFn: async () => (await api.get<Holding[]>("/portfolio/holdings")).data,
  });
}

/** 组合汇总 */
export function useSummary() {
  return useQuery({
    queryKey: ["summary"],
    queryFn: async () => (await api.get<PortfolioSummary>("/portfolio/summary")).data,
  });
}

/** 交易列表 */
export function useTransactions() {
  return useQuery({
    queryKey: ["transactions"],
    queryFn: async () => (await api.get<Transaction[]>("/transactions")).data,
  });
}

/** 日志列表 */
export function useJournals() {
  return useQuery({
    queryKey: ["journals"],
    queryFn: async () => (await api.get<Journal[]>("/journals")).data,
  });
}

/** 单篇日志 */
export function useJournal(id: number) {
  return useQuery({
    queryKey: ["journal", id],
    queryFn: async () => (await api.get<Journal>(`/journals/${id}`)).data,
    enabled: Number.isFinite(id),
  });
}

/** 股票搜索 */
export function useStockSearch(q: string) {
  return useQuery({
    queryKey: ["stock-search", q],
    queryFn: async () =>
      (await api.get<Stock[]>(`/stocks/search?q=${encodeURIComponent(q)}`)).data,
    enabled: q.length > 0,
  });
}

/** 录入交易（含强制日志） */
export function useCreateTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: TransactionCreate) =>
      (await api.post<{ transaction: Transaction; journal_id: number }>("/transactions", payload)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["holdings"] });
      qc.invalidateQueries({ queryKey: ["summary"] });
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["journals"] });
    },
  });
}

/** 登记股票 */
export function useCreateStock() {
  return useMutation({
    mutationFn: async (payload: Partial<Stock>) => (await api.post<Stock>("/stocks", payload)).data,
  });
}
