"use client";

import { Check, Pencil, Trash2, X } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { formatDate, formatMoney } from "@/lib/format";
import {
  useAccounts,
  useCashFlows,
  useCreateAccount,
  useCreateCashFlow,
  useDeleteAccount,
  useUpdateAccount,
} from "@/lib/hooks/use-cash";
import { cn } from "@/lib/utils";

const FLOW_LABELS: Record<string, string> = {
  DEPOSIT: "入金",
  WITHDRAW: "出金",
  DIVIDEND: "分红",
  INTEREST: "利息",
  TRADE_BUY: "买入",
  TRADE_SELL: "卖出",
  FEE: "费用",
  TAX: "税",
  FX: "换汇",
};

const CCY_OPTIONS = ["JPY", "USD", "CNY", "HKD"].map((c) => ({ value: c, label: c }));
const FLOW_OPTIONS = ["DEPOSIT", "WITHDRAW", "DIVIDEND", "INTEREST"].map((t) => ({
  value: t,
  label: FLOW_LABELS[t],
}));

export default function CashPage() {
  const { data: accounts } = useAccounts();
  const [selected, setSelected] = useState<number | undefined>(undefined);
  const { data: flows } = useCashFlows(selected);
  const createAccount = useCreateAccount();
  const updateAccount = useUpdateAccount();
  const deleteAccount = useDeleteAccount();
  const createFlow = useCreateCashFlow();

  const [accName, setAccName] = useState("");
  const [accCcy, setAccCcy] = useState("JPY");
  const [flowType, setFlowType] = useState("DEPOSIT");
  const [flowAmount, setFlowAmount] = useState("");

  // 内联编辑账户名
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const activeAccount = accounts?.find((a) => a.id === selected) ?? accounts?.[0];

  const submitFlow = () => {
    if (!activeAccount || !flowAmount) return;
    const signed =
      flowType === "WITHDRAW" && !flowAmount.startsWith("-") ? `-${flowAmount}` : flowAmount;
    createFlow.mutate(
      { account_id: activeAccount.id, type: flowType, amount: signed },
      { onSuccess: () => setFlowAmount("") },
    );
  };

  const saveEdit = (id: number) => {
    if (!editName.trim()) return;
    updateAccount.mutate({ id, name: editName.trim() }, { onSuccess: () => setEditingId(null) });
  };

  const onDelete = (id: number) => {
    setErr(null);
    deleteAccount.mutate(id, {
      onError: (e) => setErr((e as Error).message),
      onSuccess: () => {
        if (selected === id) setSelected(undefined);
      },
    });
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-display text-secondary">现金流</h1>
        <p className="mt-2 text-meta text-tertiary">多币种现金账户与流水。</p>
      </div>

      {err && (
        <div className="rounded-md border border-danger/40 bg-danger/10 px-4 py-2.5 text-meta text-danger">
          {err}
        </div>
      )}

      {/* 账户卡片 */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {(accounts ?? []).map((a) => {
          const active = (selected ?? accounts?.[0]?.id) === a.id;
          const editing = editingId === a.id;
          return (
            <div
              key={a.id}
              onClick={() => !editing && setSelected(a.id)}
              className={cn(
                "card-shadow group relative cursor-pointer rounded-card border bg-surface px-5 py-4 transition-colors",
                active ? "border-border-strong" : "border-border-default hover:border-border-strong",
              )}
            >
              <div className="flex items-center justify-between">
                {editing ? (
                  <input
                    autoFocus
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") saveEdit(a.id);
                      if (e.key === "Escape") setEditingId(null);
                    }}
                    className="w-32 rounded-md border border-border-strong bg-base px-2 py-0.5 text-body text-primary outline-none"
                  />
                ) : (
                  <span className="text-body font-medium text-primary">{a.name}</span>
                )}
                <span className="rounded-badge border border-border-default bg-elevated px-1.5 py-0.5 text-badge text-secondary">
                  {a.currency}
                </span>
              </div>
              <div className="tnum mt-3 text-mono-lg text-primary">{formatMoney(a.balance, a.currency)}</div>
              {a.broker && <div className="mt-1 text-caption text-tertiary">{a.broker}</div>}

              {/* 操作按钮（hover 显示） */}
              <div
                className="absolute right-3 top-3 flex gap-1 opacity-0 transition-opacity group-hover:opacity-100"
                onClick={(e) => e.stopPropagation()}
              >
                {editing ? (
                  <>
                    <button
                      onClick={() => saveEdit(a.id)}
                      className="flex h-6 w-6 items-center justify-center rounded text-tertiary hover:bg-elevated hover:text-up"
                    >
                      <Check className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => setEditingId(null)}
                      className="flex h-6 w-6 items-center justify-center rounded text-tertiary hover:bg-elevated hover:text-primary"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={() => {
                        setEditingId(a.id);
                        setEditName(a.name);
                      }}
                      className="flex h-6 w-6 items-center justify-center rounded text-tertiary hover:bg-elevated hover:text-primary"
                      aria-label="改名"
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => onDelete(a.id)}
                      className="flex h-6 w-6 items-center justify-center rounded text-tertiary hover:bg-elevated hover:text-danger"
                      aria-label="删除"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* 操作面板 */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>新建账户</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-1">
                <Label>名称</Label>
                <Input value={accName} onChange={(e) => setAccName(e.target.value)} placeholder="如 富途港股" />
              </div>
              <div className="space-y-1">
                <Label>币种</Label>
                <Select value={accCcy} onValueChange={setAccCcy} options={CCY_OPTIONS} />
              </div>
              <Button
                className="w-full"
                disabled={!accName || createAccount.isPending}
                onClick={() =>
                  createAccount.mutate(
                    { name: accName, currency: accCcy },
                    { onSuccess: () => setAccName("") },
                  )
                }
              >
                创建账户
              </Button>
            </CardContent>
          </Card>

          {activeAccount && (
            <Card>
              <CardHeader>
                <CardTitle>记一笔现金流</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="space-y-1">
                  <Label>类型</Label>
                  <Select value={flowType} onValueChange={setFlowType} options={FLOW_OPTIONS} />
                </div>
                <div className="space-y-1">
                  <Label>金额（{activeAccount.currency}）</Label>
                  <Input
                    className="tnum"
                    value={flowAmount}
                    onChange={(e) => setFlowAmount(e.target.value)}
                    placeholder="出金会自动取负"
                  />
                </div>
                <Button className="w-full" disabled={!flowAmount || createFlow.isPending} onClick={submitFlow}>
                  记录到 {activeAccount.name}
                </Button>
              </CardContent>
            </Card>
          )}
        </div>

        {/* 流水表 */}
        <Card className="overflow-hidden lg:col-span-2">
          <div className="grid grid-cols-[1fr_1fr_1fr] items-center gap-4 bg-elevated px-5 py-2.5 label-caps">
            <div>日期</div>
            <div>类型</div>
            <div className="text-right">金额</div>
          </div>
          {!flows || flows.length === 0 ? (
            <div className="px-5 py-12 text-center text-tertiary">该账户暂无流水。</div>
          ) : (
            flows.map((f) => {
              const amt = Number(f.amount);
              return (
                <div
                  key={f.id}
                  className="grid grid-cols-[1fr_1fr_1fr] items-center gap-4 border-b border-border-default px-5 py-3 last:border-b-0"
                >
                  <div className="tnum text-secondary">{formatDate(f.flow_date)}</div>
                  <div className="text-primary">{FLOW_LABELS[f.type] ?? f.type}</div>
                  <div className={cn("tnum text-right", amt >= 0 ? "text-up" : "text-down")}>
                    {formatMoney(f.amount, f.currency, { sign: true })}
                  </div>
                </div>
              );
            })
          )}
        </Card>
      </div>
    </div>
  );
}
