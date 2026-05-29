"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { useAiBudget, useAiChat, type ContextRef } from "@/lib/hooks/use-ai";
import { useHoldings } from "@/lib/hooks/use-portfolio";
import { formatMoney } from "@/lib/format";

interface Msg {
  role: "user" | "ai";
  text: string;
  meta?: { model: string; cost: string | null; cached: boolean };
}

export default function AiChatPage() {
  const { data: budget } = useAiBudget();
  const { data: holdings } = useHoldings();
  const chat = useAiChat();

  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [selected, setSelected] = useState<ContextRef[]>([]);

  const toggleHolding = (stockId: number) => {
    setSelected((prev) =>
      prev.some((r) => r.type === "HOLDING" && r.id === stockId)
        ? prev.filter((r) => !(r.type === "HOLDING" && r.id === stockId))
        : [...prev, { type: "HOLDING", id: stockId }],
    );
  };

  const send = () => {
    if (!input.trim()) return;
    const userMsg = input.trim();
    setMessages((m) => [...m, { role: "user", text: userMsg }]);
    setInput("");
    chat.mutate(
      { message: userMsg, context_refs: selected },
      {
        onSuccess: (data) => {
          setMessages((m) => [
            ...m,
            {
              role: "ai",
              text: data.response,
              meta: { model: data.model, cost: data.cost_jpy, cached: data.cached },
            },
          ]);
        },
        onError: (e) => {
          setMessages((m) => [...m, { role: "ai", text: `出错：${(e as Error).message}` }]);
        },
      },
    );
  };

  const usagePct = budget ? Math.round(budget.usage_ratio * 100) : 0;

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-h1 text-primary">AI 对话</h1>
          <p className="text-small text-secondary">基于你的持仓与日志的投资教练。</p>
        </div>
        {/* 预算进度条 */}
        {budget && (
          <div className="w-64">
            <div className="flex justify-between text-caption text-secondary">
              <span>本月 AI 预算</span>
              <span className="tnum">
                {formatMoney(budget.used_jpy)} / {formatMoney(budget.monthly_budget_jpy)}
              </span>
            </div>
            <div className="mt-1 h-2 overflow-hidden rounded-full bg-elevated">
              <div
                className={`h-full ${budget.is_close ? "bg-warn" : "bg-accent"}`}
                style={{ width: `${Math.min(usagePct, 100)}%` }}
              />
            </div>
          </div>
        )}
      </div>

      <div className="grid flex-1 grid-cols-4 gap-4 overflow-hidden">
        {/* Context 选择 */}
        <Card className="overflow-y-auto">
          <CardHeader>
            <CardTitle>引用上下文</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            {(holdings ?? []).length === 0 ? (
              <p className="text-caption text-secondary">暂无持仓</p>
            ) : (
              (holdings ?? []).map((h) => {
                const on = selected.some((r) => r.type === "HOLDING" && r.id === h.stock_id);
                return (
                  <button
                    key={h.stock_id}
                    onClick={() => toggleHolding(h.stock_id)}
                    className={`flex w-full items-center justify-between rounded-md px-2 py-1.5 text-small ${
                      on ? "bg-accent/10 text-accent" : "text-secondary hover:bg-elevated"
                    }`}
                  >
                    <span>{h.name}</span>
                    <span className="tnum text-caption">{h.symbol}</span>
                  </button>
                );
              })
            )}
          </CardContent>
        </Card>

        {/* 对话区 */}
        <Card className="col-span-3 flex flex-col overflow-hidden">
          <CardContent className="flex flex-1 flex-col gap-3 overflow-y-auto p-4">
            {messages.length === 0 ? (
              <div className="flex flex-1 items-center justify-center text-small text-secondary">
                选择左侧持仓作为上下文，提问吧。
              </div>
            ) : (
              messages.map((m, i) => (
                <div
                  key={i}
                  className={`max-w-[80%] rounded-lg px-3 py-2 text-small ${
                    m.role === "user"
                      ? "self-end bg-accent/10 text-primary"
                      : "self-start bg-elevated text-primary"
                  }`}
                >
                  <div className="whitespace-pre-wrap">{m.text}</div>
                  {m.meta && (
                    <div className="mt-1 text-caption text-muted">
                      {m.meta.model} · {m.meta.cached ? "缓存命中" : formatMoney(m.meta.cost)}
                    </div>
                  )}
                </div>
              ))
            )}
            {chat.isPending && (
              <div className="self-start text-small text-secondary">思考中…</div>
            )}
          </CardContent>
          <div className="border-t border-border-subtle p-3">
            <div className="flex gap-2">
              <Textarea
                rows={2}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) send();
                }}
                placeholder="问 AI 教练…（Cmd/Ctrl+Enter 发送）"
              />
              <Button onClick={send} disabled={chat.isPending || !input.trim()}>
                发送
              </Button>
            </div>
            <p className="mt-2 text-caption text-muted">
              AI 仅供参考，不构成投资建议，不显示买卖信号。
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
}
