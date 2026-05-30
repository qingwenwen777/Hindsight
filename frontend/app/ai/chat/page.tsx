"use client";

import { Bot, MessageSquarePlus, Pencil, Plus, Send, Trash2, User, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import {
  streamConversationChat,
  useAiBudget,
  useConversation,
  useConversations,
  useCreateConversation,
  useDeleteConversation,
  useRenameConversation,
  type ContextRef,
} from "@/lib/hooks/use-ai";
import { useHoldings } from "@/lib/hooks/use-portfolio";
import { useT } from "@/lib/i18n/use-t";
import { cn } from "@/lib/utils";

interface Msg {
  role: "user" | "ai";
  text: string;
  streaming?: boolean;
  meta?: { model: string; promptTokens: number; completionTokens: number; cached: boolean };
}

/** 紧凑显示 token 数（1234 -> 1.2k）。 */
function formatTokens(n: number): string {
  if (n < 1000) return String(n);
  return `${(n / 1000).toFixed(n < 10000 ? 1 : 0)}k`;
}

export default function AiChatPage() {
  const { t } = useT();
  const qc = useQueryClient();
  const { data: budget } = useAiBudget();
  const { data: holdings } = useHoldings();
  const { data: conversations } = useConversations();
  const createConv = useCreateConversation();
  const renameConv = useRenameConversation();
  const deleteConv = useDeleteConversation();

  const [activeId, setActiveId] = useState<number | null>(null);
  const { data: activeConv } = useConversation(activeId);

  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [selected, setSelected] = useState<ContextRef[]>([]);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [sending, setSending] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);
  const pickerRef = useRef<HTMLDivElement>(null);

  const SUGGESTIONS = [t("ai.suggestion.1"), t("ai.suggestion.2"), t("ai.suggestion.3")];

  // 点击外部 / 按 Esc 关闭上下文选择器
  useEffect(() => {
    if (!pickerOpen) return;
    const onPointerDown = (e: MouseEvent) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target as Node)) {
        setPickerOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setPickerOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [pickerOpen]);

  // 切换会话时，把持久化的历史消息载入视图（流式发送中不覆盖）
  useEffect(() => {
    if (sending) return;
    if (activeId == null) {
      setMessages([]);
      return;
    }
    if (activeConv?.messages) {
      setMessages(
        activeConv.messages.map((m) => ({
          role: m.role === "assistant" ? "ai" : "user",
          text: m.content,
          meta:
            m.role === "assistant" && m.model
              ? {
                  model: m.model,
                  promptTokens: m.prompt_tokens ?? 0,
                  completionTokens: m.completion_tokens ?? 0,
                  cached: m.cached,
                }
              : undefined,
        })),
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeId, activeConv]);

  // 自动滚到底
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sending]);

  // textarea 自适应高度
  const autosize = () => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 200)}px`;
  };

  const toggleHolding = (stockId: number) => {
    setSelected((prev) =>
      prev.some((r) => r.type === "HOLDING" && r.id === stockId)
        ? prev.filter((r) => !(r.type === "HOLDING" && r.id === stockId))
        : [...prev, { type: "HOLDING", id: stockId }],
    );
  };

  const startNewChat = () => {
    if (sending) return;
    setActiveId(null);
    setMessages([]);
    setInput("");
    taRef.current?.focus();
  };

  const selectConversation = (id: number) => {
    if (sending) return;
    setActiveId(id);
  };

  const handleRename = async (id: number, current: string) => {
    const title = window.prompt(t("ai.renamePrompt"), current);
    if (title && title.trim()) await renameConv.mutateAsync({ id, title: title.trim() });
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm(t("ai.deleteConfirm"))) return;
    await deleteConv.mutateAsync(id);
    if (activeId === id) startNewChat();
  };

  const send = async (preset?: string) => {
    const userMsg = (preset ?? input).trim();
    if (!userMsg || sending) return;
    setSending(true);

    // 确保有一个会话；没有则先创建
    let convId = activeId;
    if (convId == null) {
      try {
        const created = await createConv.mutateAsync(undefined);
        convId = created.id;
        setActiveId(created.id);
      } catch (e) {
        setSending(false);
        setMessages((m) => [...m, { role: "ai", text: `${t("ai.errorPrefix")}${(e as Error).message}` }]);
        return;
      }
    }

    setMessages((m) => [
      ...m,
      { role: "user", text: userMsg },
      { role: "ai", text: "", streaming: true },
    ]);
    setInput("");
    if (taRef.current) taRef.current.style.height = "auto";

    const refs = selected;
    const appendDelta = (delta: string) =>
      setMessages((m) => {
        const next = [...m];
        const last = next[next.length - 1];
        if (last && last.role === "ai") next[next.length - 1] = { ...last, text: last.text + delta };
        return next;
      });

    try {
      await streamConversationChat(
        convId,
        { message: userMsg, context_refs: refs },
        {
          onDelta: appendDelta,
          onTitle: () => qc.invalidateQueries({ queryKey: ["conversations"] }),
          onDone: (d) =>
            setMessages((m) => {
              const next = [...m];
              const last = next[next.length - 1];
              if (last && last.role === "ai") {
                next[next.length - 1] = {
                  ...last,
                  streaming: false,
                  meta: {
                    model: d.model,
                    promptTokens: d.prompt_tokens,
                    completionTokens: d.completion_tokens,
                    cached: d.cached,
                  },
                };
              }
              return next;
            }),
          onError: (msg) =>
            setMessages((m) => {
              const next = [...m];
              const last = next[next.length - 1];
              if (last && last.role === "ai") {
                next[next.length - 1] = {
                  ...last,
                  streaming: false,
                  text: last.text || `${t("ai.errorPrefix")}${msg}`,
                };
              }
              return next;
            }),
        },
      );
    } catch (e) {
      setMessages((m) => {
        const next = [...m];
        const last = next[next.length - 1];
        if (last && last.role === "ai") {
          next[next.length - 1] = {
            ...last,
            streaming: false,
            text: last.text || `${t("ai.errorPrefix")}${(e as Error).message}`,
          };
        }
        return next;
      });
    } finally {
      setSending(false);
      // 刷新会话列表（更新时间/标题）与当前会话缓存
      qc.invalidateQueries({ queryKey: ["conversations"] });
      if (convId != null) qc.invalidateQueries({ queryKey: ["conversation", convId] });
      qc.invalidateQueries({ queryKey: ["ai-budget"] });
    }
  };

  const selectedHoldings = (holdings ?? []).filter((h) =>
    selected.some((r) => r.type === "HOLDING" && r.id === h.stock_id),
  );
  const empty = messages.length === 0;

  return (
    <div className="flex h-[calc(100vh-60px-3rem)] w-full">
      {/* 左侧：会话列表 */}
      <aside className="hidden w-64 shrink-0 flex-col border-r border-border-subtle pr-4 md:flex">
        <button
          onClick={startNewChat}
          disabled={sending}
          className="mb-4 flex items-center justify-center gap-2 rounded-lg border border-border-default bg-surface px-3 py-2.5 text-body font-medium text-secondary transition-colors hover:border-border-strong hover:text-primary disabled:opacity-40"
        >
          <MessageSquarePlus className="h-4 w-4" />
          {t("ai.newChat")}
        </button>
        <div className="px-1 pb-1.5 label-caps">{t("ai.history")}</div>
        <div className="-mr-1 flex-1 overflow-y-auto pr-1">
          {(conversations ?? []).length === 0 ? (
            <p className="px-2 py-2 text-caption text-tertiary">{t("ai.noConversations")}</p>
          ) : (
            <div className="grid gap-0.5">
              {(conversations ?? []).map((c) => {
                const active = c.id === activeId;
                return (
                  <div
                    key={c.id}
                    className={cn(
                      "group flex items-center gap-1 rounded-lg px-2.5 py-2 text-body transition-colors",
                      active
                        ? "bg-elevated text-primary"
                        : "text-tertiary hover:bg-elevated/60 hover:text-primary",
                    )}
                  >
                    <button
                      onClick={() => selectConversation(c.id)}
                      className="flex min-w-0 flex-1 items-center gap-2 text-left"
                      title={c.title}
                    >
                      <Bot className="h-3.5 w-3.5 shrink-0 opacity-60" />
                      <span className="truncate">{c.title || t("ai.untitled")}</span>
                    </button>
                    <button
                      onClick={() => handleRename(c.id, c.title)}
                      className="hidden h-6 w-6 shrink-0 items-center justify-center rounded text-tertiary hover:text-primary group-hover:flex"
                      aria-label={t("ai.rename")}
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => handleDelete(c.id)}
                      className="hidden h-6 w-6 shrink-0 items-center justify-center rounded text-tertiary hover:text-down group-hover:flex"
                      aria-label={t("ai.delete")}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </aside>

      {/* 右侧：对话主区 */}
      <div className="flex min-w-0 flex-1 flex-col md:pl-6">
        {/* 顶部：标题 + 预算 */}
        <div className="mx-auto flex w-full max-w-3xl items-center justify-between pb-4">
          <div className="flex items-center gap-2">
            {/* 移动端的新建按钮 */}
            <button
              onClick={startNewChat}
              disabled={sending}
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-border-default text-secondary hover:text-primary disabled:opacity-40 md:hidden"
              aria-label={t("ai.newChat")}
            >
              <MessageSquarePlus className="h-4 w-4" />
            </button>
            <div>
              <h1 className="text-title font-medium text-primary">{t("ai.title")}</h1>
              <p className="text-caption text-tertiary">{t("ai.subtitle")}</p>
            </div>
          </div>
          {budget && (
            <div className="text-right">
              <div className="text-caption text-tertiary">{t("ai.monthlyTokens")}</div>
              <div className="tnum text-body text-secondary">
                {formatTokens(budget.total_tokens)}
                <span className="text-caption text-tertiary"> · {t("ai.calls", { n: budget.calls })}</span>
              </div>
            </div>
          )}
        </div>

        {/* 对话区 */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-3xl">
            {empty ? (
              <div className="flex h-full min-h-[50vh] flex-col items-center justify-center gap-6 px-4 text-center">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-elevated">
                  <Bot className="h-7 w-7 text-primary" />
                </div>
                <div>
                  <h2 className="text-display text-primary">{t("ai.empty.title")}</h2>
                  <p className="mt-2 text-meta text-tertiary">{t("ai.empty.desc")}</p>
                </div>
                <div className="flex w-full max-w-md flex-col gap-2">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => send(s)}
                      className="rounded-lg border border-border-default bg-surface px-4 py-3 text-left text-body text-secondary transition-colors hover:border-border-strong hover:text-primary"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-6 px-1 pb-4">
                {messages.map((m, i) => (
                  <div key={i} className="flex gap-4">
                    <div
                      className={cn(
                        "flex h-8 w-8 shrink-0 items-center justify-center rounded-md",
                        m.role === "user" ? "bg-elevated" : "bg-primary text-base",
                      )}
                    >
                      {m.role === "user" ? (
                        <User className="h-4 w-4 text-secondary" />
                      ) : (
                        <Bot className="h-4 w-4" />
                      )}
                    </div>
                    <div className="min-w-0 flex-1 pt-0.5">
                      <div className="mb-1 text-caption font-medium text-tertiary">
                        {m.role === "user" ? t("ai.you") : t("ai.coach")}
                      </div>
                      {m.role === "ai" && m.streaming && m.text === "" ? (
                        <div className="flex items-center gap-1 pt-1.5">
                          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-tertiary [animation-delay:-0.3s]" />
                          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-tertiary [animation-delay:-0.15s]" />
                          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-tertiary" />
                        </div>
                      ) : (
                        <div className="whitespace-pre-wrap text-body leading-relaxed text-primary">
                          {m.text}
                          {m.role === "ai" && m.streaming && (
                            <span className="ml-0.5 inline-block h-4 w-[2px] translate-y-0.5 animate-pulse bg-primary align-middle" />
                          )}
                        </div>
                      )}
                      {m.meta && (
                        <div className="mt-2 flex flex-wrap items-center gap-2 text-caption text-muted">
                          <span className="rounded border border-border-default px-1.5 py-0.5">
                            {m.meta.model}
                          </span>
                          {m.meta.cached ? (
                            <span>{t("ai.cached")}</span>
                          ) : (
                            <span className="tnum">
                              {t("ai.tokensDetail", {
                                total: m.meta.promptTokens + m.meta.completionTokens,
                                prompt: m.meta.promptTokens,
                                completion: m.meta.completionTokens,
                              })}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* 输入区（ChatGPT 风格合成器） */}
        <div className="mx-auto w-full max-w-3xl pt-3">
          {selectedHoldings.length > 0 && (
            <div className="mb-2 flex flex-wrap gap-1.5">
              {selectedHoldings.map((h) => (
                <span
                  key={h.stock_id}
                  className="inline-flex items-center gap-1 rounded-full border border-border-default bg-elevated px-2 py-1 text-caption text-secondary"
                >
                  {h.symbol}
                  <button onClick={() => toggleHolding(h.stock_id)} className="hover:text-primary">
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          )}

          <div className="relative rounded-2xl border border-border-default bg-surface focus-within:border-border-strong">
            <textarea
              ref={taRef}
              rows={1}
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                autosize();
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
              placeholder={t("ai.inputPlaceholder")}
              className="block max-h-[200px] w-full resize-none bg-transparent px-4 pb-12 pt-3.5 text-body text-primary outline-none placeholder:text-tertiary"
            />
            <div className="absolute inset-x-2 bottom-2 flex items-center justify-between">
              <div className="relative" ref={pickerRef}>
                <button
                  onClick={() => setPickerOpen((o) => !o)}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-border-default px-2.5 py-1.5 text-caption text-secondary hover:bg-elevated hover:text-primary"
                >
                  <Plus className="h-3.5 w-3.5" />
                  {t("ai.context")}
                  {selected.length > 0 && (
                    <span className="tnum rounded-full bg-elevated px-1.5 text-caption">
                      {selected.length}
                    </span>
                  )}
                </button>
                {pickerOpen && (
                  <div className="absolute bottom-full left-0 mb-2 max-h-64 w-64 overflow-y-auto rounded-lg border border-border-strong bg-elevated p-1 shadow-xl">
                    {(holdings ?? []).length === 0 ? (
                      <p className="px-3 py-2 text-caption text-tertiary">{t("ai.noHoldings")}</p>
                    ) : (
                      (holdings ?? []).map((h) => {
                        const on = selected.some((r) => r.type === "HOLDING" && r.id === h.stock_id);
                        return (
                          <button
                            key={h.stock_id}
                            onClick={() => toggleHolding(h.stock_id)}
                            className={cn(
                              "flex w-full items-center justify-between rounded-md px-3 py-2 text-body",
                              on ? "bg-base text-primary" : "text-secondary hover:bg-base",
                            )}
                          >
                            <span className="truncate">{h.name}</span>
                            <span className="tnum text-caption text-tertiary">{h.symbol}</span>
                          </button>
                        );
                      })
                    )}
                  </div>
                )}
              </div>
              <button
                onClick={() => send()}
                disabled={sending || !input.trim()}
                className="flex h-8 w-8 items-center justify-center rounded-lg bg-btn-primary text-btn-primary-fg transition-opacity hover:opacity-90 disabled:opacity-30"
                aria-label={t("ai.send")}
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
          <p className="mt-2 text-center text-caption text-muted">{t("ai.disclaimer")}</p>
        </div>
      </div>
    </div>
  );
}
