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

export function useCreateAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { name: string; currency: string; broker?: string }) =>
      (await api.post<CashAccount>("/portfolio/accounts", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cash-accounts"] }),
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
