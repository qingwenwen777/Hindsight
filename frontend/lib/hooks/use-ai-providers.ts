"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";

export interface AiProvider {
  id: number;
  name: string;
  protocol: "openai" | "anthropic";
  base_url: string;
  api_key_mask: string;
  has_key: boolean;
  models: string[];
  default_model: string | null;
  enabled: boolean;
  is_default: boolean;
  updated_at: string | null;
}

export interface ProviderInput {
  name?: string;
  protocol?: string;
  base_url?: string;
  api_key?: string;
  models?: string[];
  default_model?: string | null;
  enabled?: boolean;
  is_default?: boolean;
}

export function useAiProviders() {
  return useQuery({
    queryKey: ["ai-providers"],
    queryFn: async () => (await api.get<AiProvider[]>("/ai-providers")).data,
  });
}

export function useCreateProvider() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: ProviderInput) =>
      (await api.post<AiProvider>("/ai-providers", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ai-providers"] }),
  });
}

export function useUpdateProvider() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...body }: ProviderInput & { id: number }) =>
      (await api.patch<AiProvider>(`/ai-providers/${id}`, body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ai-providers"] }),
  });
}

export function useDeleteProvider() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await api.delete<{ deleted: number }>(`/ai-providers/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ai-providers"] }),
  });
}

export function useSetDefaultProvider() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await api.post<AiProvider>(`/ai-providers/${id}/default`, {})).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ai-providers"] }),
  });
}

export interface ProbeBody {
  provider_id?: number;
  protocol?: string;
  base_url?: string;
  api_key?: string;
  model?: string;
}

export function useFetchModels() {
  return useMutation({
    mutationFn: async (body: ProbeBody) =>
      (await api.post<{ models: string[] }>("/ai-providers/fetch-models", body)).data,
  });
}

export function useTestConnection() {
  return useMutation({
    mutationFn: async (body: ProbeBody) =>
      (await api.post<{ ok: boolean; message: string }>("/ai-providers/test", body)).data,
  });
}
