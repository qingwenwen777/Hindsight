"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";

export interface AiBudget {
  monthly_budget_jpy: string;
  used_jpy: string;
  remaining_jpy: string;
  usage_ratio: number;
  is_close: boolean;
  available: boolean;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  calls: number;
}

export interface ChatResponse {
  response: string;
  model: string;
  cached: boolean;
  degraded: boolean;
  cost_jpy: string | null;
  prompt_tokens: number;
  completion_tokens: number;
}

export interface ContextRef {
  type: "HOLDING" | "TRANSACTION" | "JOURNAL";
  id: number;
}

export function useAiBudget() {
  return useQuery({
    queryKey: ["ai-budget"],
    queryFn: async () => (await api.get<AiBudget>("/ai/budget")).data,
  });
}

export function useAiChat() {
  return useMutation({
    mutationFn: async (body: { message: string; context_refs: ContextRef[] }) =>
      (await api.post<ChatResponse>("/ai/chat", body)).data,
  });
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_PREFIX = "/api/v1";

export interface ChatStreamHandlers {
  onMeta?: (m: { model: string; cached: boolean; degraded: boolean }) => void;
  onDelta?: (text: string) => void;
  onDone?: (d: {
    model: string;
    cached: boolean;
    degraded: boolean;
    cost_jpy: string | null;
    prompt_tokens: number;
    completion_tokens: number;
  }) => void;
  onError?: (message: string) => void;
}

/**
 * 流式对话：通过 SSE 逐段接收 AI 输出。
 * 返回 abort 函数，可用于取消请求。
 */
export function streamAiChat(
  body: { message: string; context_refs: ContextRef[] },
  handlers: ChatStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  return (async () => {
    const resp = await fetch(`${API_BASE}${API_PREFIX}/ai/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    });

    if (!resp.ok || !resp.body) {
      // 尝试解析统一错误壳
      let msg = `请求失败 (HTTP ${resp.status})`;
      try {
        const j = await resp.json();
        if (j?.message) msg = j.message;
      } catch {
        /* ignore */
      }
      handlers.onError?.(msg);
      return;
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    const handleEvent = (raw: string) => {
      // 每条 SSE 记录可能有多行 data:
      const dataLines = raw
        .split("\n")
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.slice(5).trim());
      if (dataLines.length === 0) return;
      const payload = dataLines.join("\n");
      let evt: Record<string, unknown>;
      try {
        evt = JSON.parse(payload);
      } catch {
        return;
      }
      switch (evt.type) {
        case "meta":
          handlers.onMeta?.({
            model: String(evt.model ?? ""),
            cached: Boolean(evt.cached),
            degraded: Boolean(evt.degraded),
          });
          break;
        case "delta":
          handlers.onDelta?.(String(evt.text ?? ""));
          break;
        case "done":
          handlers.onDone?.({
            model: String(evt.model ?? ""),
            cached: Boolean(evt.cached),
            degraded: Boolean(evt.degraded),
            cost_jpy: (evt.cost_jpy as string | null) ?? null,
            prompt_tokens: Number(evt.prompt_tokens ?? 0),
            completion_tokens: Number(evt.completion_tokens ?? 0),
          });
          break;
        case "error":
          handlers.onError?.(String(evt.message ?? "未知错误"));
          break;
      }
    };

    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      // SSE 事件以空行分隔
      let sep: number;
      while ((sep = buffer.indexOf("\n\n")) !== -1) {
        const raw = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        handleEvent(raw);
      }
    }
    // flush 残留
    if (buffer.trim()) handleEvent(buffer);
  })();
}

export function useAiInsights() {
  return useQuery({
    queryKey: ["ai-insights"],
    queryFn: async () =>
      (
        await api.get<
          {
            id: number;
            prompt_type: string;
            model: string;
            cost_jpy: string | null;
            response: string;
            created_at: string | null;
          }[]
        >("/ai/insights")
      ).data,
  });
}

// ===== 对话持久化 =====

export interface ConversationBrief {
  id: number;
  title: string;
  created_at: string | null;
  updated_at: string | null;
  message_count?: number;
}

export interface ConversationMessage {
  id: number;
  conversation_id: number;
  role: "user" | "assistant";
  content: string;
  model: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  cost_jpy: string | null;
  cached: boolean;
  context_refs: { type: string; id: number }[] | null;
  created_at: string | null;
}

export interface ConversationDetail extends ConversationBrief {
  messages: ConversationMessage[];
}

export function useConversations() {
  return useQuery({
    queryKey: ["conversations"],
    queryFn: async () => (await api.get<ConversationBrief[]>("/conversations")).data,
  });
}

export function useConversation(id: number | null) {
  return useQuery({
    queryKey: ["conversation", id],
    enabled: id != null,
    queryFn: async () => (await api.get<ConversationDetail>(`/conversations/${id}`)).data,
  });
}

export function useCreateConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (title?: string) =>
      (await api.post<ConversationBrief>("/conversations", { title })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["conversations"] }),
  });
}

export function useRenameConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, title }: { id: number; title: string }) =>
      (await api.patch<ConversationBrief>(`/conversations/${id}`, { title })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["conversations"] }),
  });
}

export function useDeleteConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await api.delete<{ id: number; deleted: boolean }>(`/conversations/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["conversations"] }),
  });
}

export interface ConvChatStreamHandlers extends ChatStreamHandlers {
  onTitle?: (title: string) => void;
}

/**
 * 在某会话内流式提问（自动持久化）。
 */
export function streamConversationChat(
  conversationId: number,
  body: { message: string; context_refs: ContextRef[] },
  handlers: ConvChatStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  return (async () => {
    const resp = await fetch(
      `${API_BASE}${API_PREFIX}/conversations/${conversationId}/chat/stream`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal,
      },
    );

    if (!resp.ok || !resp.body) {
      let msg = `请求失败 (HTTP ${resp.status})`;
      try {
        const j = await resp.json();
        if (j?.message) msg = j.message;
      } catch {
        /* ignore */
      }
      handlers.onError?.(msg);
      return;
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    const handleEvent = (raw: string) => {
      const dataLines = raw
        .split("\n")
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.slice(5).trim());
      if (dataLines.length === 0) return;
      let evt: Record<string, unknown>;
      try {
        evt = JSON.parse(dataLines.join("\n"));
      } catch {
        return;
      }
      switch (evt.type) {
        case "title":
          handlers.onTitle?.(String(evt.title ?? ""));
          break;
        case "meta":
          handlers.onMeta?.({
            model: String(evt.model ?? ""),
            cached: Boolean(evt.cached),
            degraded: Boolean(evt.degraded),
          });
          break;
        case "delta":
          handlers.onDelta?.(String(evt.text ?? ""));
          break;
        case "done":
          handlers.onDone?.({
            model: String(evt.model ?? ""),
            cached: Boolean(evt.cached),
            degraded: Boolean(evt.degraded),
            cost_jpy: (evt.cost_jpy as string | null) ?? null,
            prompt_tokens: Number(evt.prompt_tokens ?? 0),
            completion_tokens: Number(evt.completion_tokens ?? 0),
          });
          break;
        case "error":
          handlers.onError?.(String(evt.message ?? "未知错误"));
          break;
      }
    };

    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let sep: number;
      while ((sep = buffer.indexOf("\n\n")) !== -1) {
        const raw = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        handleEvent(raw);
      }
    }
    if (buffer.trim()) handleEvent(buffer);
  })();
}
