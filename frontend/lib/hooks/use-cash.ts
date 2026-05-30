"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";

export interface CashAccount {
  id: number;
  name: string;
  broker: string | null;
  currency: string;
  balance: string;
}

export interface CashFlow {
  id: number;
  account_id: number;
  flow_date: string;
  type: string;
  amount: string;
  currency: string;
  related_tx_id: number | null;
  notes: string | null;
}

export function useAccounts() {
  return useQuery({
    queryKey: ["cash-accounts"],
    queryFn: async () => (await api.get<CashAccount[]>("/portfolio/accounts")).data,
  });
}

export function useCashFlows(accountId?: number) {
  return useQuery({
    queryKey: ["cash-flows", accountId],
    queryFn: async () =>
      (await api.get<CashFlow[]>(`/portfolio/cash-flows${accountId ? `?account_id=${accountId}` : ""}`)).data,
  });
}

export interface CashSummaryRow {
  currency: string;
  balance: string;
  converted: string | null;
  rate: string | null;
  estimated: boolean;
}

export interface CashSummary {
  target_currency: string;
  by_currency: CashSummaryRow[];
  total: { currency: string; amount: string; estimated: boolean };
}

export function useCashSummary(currency: string) {
  return useQuery({
    queryKey: ["cash-summary", currency],
    queryFn: async () =>
      (await api.get<CashSummary>(`/portfolio/cash-summary?currency=${currency}`)).data,
  });
}

export function useCreateAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { name: string; currency: string; broker?: string }) =>
      (await api.post<CashAccount>("/portfolio/accounts", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cash-accounts"] }),
  });
}

export function useUpdateAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...body }: { id: number; name?: string; currency?: string; broker?: string }) =>
      (await api.patch<CashAccount>(`/portfolio/accounts/${id}`, body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cash-accounts"] }),
  });
}

export function useDeleteAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await api.delete<{ deleted: number }>(`/portfolio/accounts/${id}`)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cash-accounts"] });
      qc.invalidateQueries({ queryKey: ["cash-flows"] });
    },
  });
}

export function useCreateCashFlow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      account_id: number;
      type: string;
      amount: string;
      notes?: string;
    }) => (await api.post("/portfolio/cash-flows", body)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cash-accounts"] });
      qc.invalidateQueries({ queryKey: ["cash-flows"] });
    },
  });
}
