"use client";

import { Bot, Plus, Send, User, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { useAiBudget, useAiChat, type ContextRef } from "@/lib/hooks/use-ai";
import { useHoldings } from "@/lib/hooks/use-portfolio";
import { cn } from "@/lib/utils";

interface Msg {
  role: "user" | "ai";
  text: string;
  meta?: { model: string; promptTokens: number; completionTokens: number; cached: boolean };
}

const SUGGESTIONS = [
  "复盘我当前持仓的集中度风险",
  "用魔鬼代言人视角挑战我的多头逻辑",
  "我最近的交易里有哪些认知偏差？",
];

/** 紧凑显示 token 数（1234 -> 1.2k）。 */
function formatTokens(n: number): string {
  if (n < 1000) return String(n);
  return `${(n / 1000).toFixed(n < 10000 ? 1 : 0)}k`;
}

export default function AiChatPage() {
  const { data: budget } = useAiBudget();
  const { data: holdings } = useHoldings();
  const chat = useAiChat();

  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [selected, setSelected] = useState<ContextRef[]>([]);
  const [pickerOpen, setPickerOpen] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);

  // 自动滚到底
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, chat.isPending]);

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

  const send = (preset?: string) => {
    const userMsg = (preset ?? input).trim();
    if (!userMsg || chat.isPending) return;
    setMessages((m) => [...m, { role: "user", text: userMsg }]);
    setInput("");
    if (taRef.current) taRef.current.style.height = "auto";
    chat.mutate(
      { message: userMsg, context_refs: selected },
      {
        onSuccess: (data) =>
          setMessages((m) => [
            ...m,
            {
              role: "ai",
              text: data.response,
              meta: {
                model: data.model,
                promptTokens: data.prompt_tokens,
                completionTokens: data.completion_tokens,
                cached: data.cached,
              },
            },
          ]),
        onError: (e) =>
          setMessages((m) => [...m, { role: "ai", text: `出错：${(e as Error).message}` }]),
      },
    );
  };

  const selectedHoldings = (holdings ?? []).filter((h) =>
    selected.some((r) => r.type === "HOLDING" && r.id === h.stock_id),
  );
  const empty = messages.length === 0;

  return (
    <div className="mx-auto flex h-[calc(100vh-60px-3rem)] max-w-3xl flex-col">
      {/* 顶部：标题 + 预算 */}
      <div className="flex items-center justify-between pb-4">
        <div>
          <h1 className="text-title font-medium text-primary">AI 投资教练</h1>
          <p className="text-caption text-tertiary">基于你的持仓与日志 · 仅定性分析</p>
        </div>
        {budget && (
          <div className="text-right">
            <div className="text-caption text-tertiary">本月 Token 用量</div>
            <div className="tnum text-body text-secondary">
              {formatTokens(budget.total_tokens)}
              <span className="text-caption text-tertiary"> · {budget.calls} 次对话</span>
            </div>
          </div>
        )}
      </div>

      {/* 对话区 */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        {empty ? (
          <div className="flex h-full flex-col items-center justify-center gap-6 px-4 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-elevated">
              <Bot className="h-7 w-7 text-primary" />
            </div>
            <div>
              <h2 className="text-display text-primary">问点什么？</h2>
              <p className="mt-2 text-meta text-tertiary">
                选几个持仓作为上下文，让 AI 基于你的真实数据复盘。
              </p>
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
                    {m.role === "user" ? "你" : "AI 教练"}
                  </div>
                  <div className="whitespace-pre-wrap text-body leading-relaxed text-primary">
                    {m.text}
                  </div>
                  {m.meta && (
                    <div className="mt-2 flex flex-wrap items-center gap-2 text-caption text-muted">
                      <span className="rounded border border-border-default px-1.5 py-0.5">
                        {m.meta.model}
                      </span>
                      {m.meta.cached ? (
                        <span>缓存命中 · 未消耗 token</span>
                      ) : (
                        <span className="tnum">
                          {formatTokens(m.meta.promptTokens + m.meta.completionTokens)} tokens
                          （输入 {m.meta.promptTokens} · 输出 {m.meta.completionTokens}）
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {chat.isPending && (
              <div className="flex gap-4">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary text-base">
                  <Bot className="h-4 w-4" />
                </div>
                <div className="flex items-center gap-1 pt-2.5">
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-tertiary [animation-delay:-0.3s]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-tertiary [animation-delay:-0.15s]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-tertiary" />
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 输入区（ChatGPT 风格合成器） */}
      <div className="pt-3">
        {/* 已选上下文 chips */}
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
            placeholder="问 AI 教练…（Enter 发送，Shift+Enter 换行）"
            className="block max-h-[200px] w-full resize-none bg-transparent px-4 pb-12 pt-3.5 text-body text-primary outline-none placeholder:text-tertiary"
          />
          {/* 底部操作条 */}
          <div className="absolute inset-x-2 bottom-2 flex items-center justify-between">
            <div className="relative">
              <button
                onClick={() => setPickerOpen((o) => !o)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-border-default px-2.5 py-1.5 text-caption text-secondary hover:bg-elevated hover:text-primary"
              >
                <Plus className="h-3.5 w-3.5" />
                上下文
                {selected.length > 0 && (
                  <span className="tnum rounded-full bg-elevated px-1.5 text-caption">
                    {selected.length}
                  </span>
                )}
              </button>
              {pickerOpen && (
                <div className="absolute bottom-full left-0 mb-2 max-h-64 w-64 overflow-y-auto rounded-lg border border-border-strong bg-elevated p-1 shadow-xl">
                  {(holdings ?? []).length === 0 ? (
                    <p className="px-3 py-2 text-caption text-tertiary">暂无持仓可引用</p>
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
              disabled={chat.isPending || !input.trim()}
              className="flex h-8 w-8 items-center justify-center rounded-lg bg-btn-primary text-btn-primary-fg transition-opacity hover:opacity-90 disabled:opacity-30"
              aria-label="发送"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
        <p className="mt-2 text-center text-caption text-muted">
          AI 仅供参考，不构成投资建议，不显示买卖信号。
        </p>
      </div>
    </div>
  );
}
