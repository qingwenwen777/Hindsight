"use client";

import { Check, ListOrdered, Pencil, Plus, PlusCircle, Trash2, X } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogClose, DialogContent } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { formatDate, formatMoney } from "@/lib/format";
import { useT } from "@/lib/i18n/use-t";
import {
  useAccounts,
  useCashFlows,
  useCashSummary,
  useCreateAccount,
  useCreateCashFlow,
  useDeleteAccount,
  useUpdateAccount,
  type CashAccount,
} from "@/lib/hooks/use-cash";
import { cn } from "@/lib/utils";

const FLOW_TYPE_KEYS: Record<string, string> = {
  DEPOSIT: "cash.flow.DEPOSIT",
  WITHDRAW: "cash.flow.WITHDRAW",
  DIVIDEND: "cash.flow.DIVIDEND",
  INTEREST: "cash.flow.INTEREST",
  TRADE_BUY: "cash.flow.TRADE_BUY",
  TRADE_SELL: "cash.flow.TRADE_SELL",
  FEE: "cash.flow.FEE",
  TAX: "cash.flow.TAX",
  FX: "cash.flow.FX",
};

const CURRENCIES = ["JPY", "USD", "CNY", "HKD"];
const CCY_OPTIONS = ["JPY", "USD", "CNY", "HKD"].map((c) => ({ value: c, label: c }));

export default function CashPage() {
  const { t } = useT();
  const { data: accounts } = useAccounts();
  const deleteAccount = useDeleteAccount();

  // 总览折算币种
  const [summaryCcy, setSummaryCcy] = useState("JPY");
  const { data: summary } = useCashSummary(summaryCcy);

  // 弹窗状态
  const [newAccountOpen, setNewAccountOpen] = useState(false);
  const [flowAccount, setFlowAccount] = useState<CashAccount | null>(null);
  const [flowsAccount, setFlowsAccount] = useState<CashAccount | null>(null);

  // 内联改名
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const updateAccount = useUpdateAccount();
  const [err, setErr] = useState<string | null>(null);

  const saveEdit = (id: number) => {
    if (!editName.trim()) return;
    updateAccount.mutate({ id, name: editName.trim() }, { onSuccess: () => setEditingId(null) });
  };

  const onDelete = (id: number) => {
    setErr(null);
    deleteAccount.mutate(id, { onError: (e) => setErr((e as Error).message) });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-display text-secondary">{t("cash.title")}</h1>
          <p className="mt-2 text-meta text-tertiary">{t("cash.subtitle")}</p>
        </div>
        <Button onClick={() => setNewAccountOpen(true)} className="gap-1.5">
          <Plus className="h-4 w-4" />
          {t("cash.newAccount")}
        </Button>
      </div>

      {err && (
        <div className="rounded-md border border-danger/40 bg-danger/10 px-4 py-2.5 text-meta text-danger">
          {err}
        </div>
      )}

      {/* 现金总览 */}
      <CashOverview
        summary={summary}
        summaryCcy={summaryCcy}
        onChangeCcy={setSummaryCcy}
      />

      {/* 账户卡片 */}
      {(accounts ?? []).length === 0 ? (
        <Card className="px-5 py-12 text-center text-tertiary">{t("cash.noAccounts")}</Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {(accounts ?? []).map((a) => {
            const editing = editingId === a.id;
            return (
              <div
                key={a.id}
                className="card-shadow group relative rounded-card border border-border-default bg-surface px-5 py-4 transition-colors hover:border-border-strong"
              >
                <div className="flex items-center justify-between">
                  {editing ? (
                    <input
                      autoFocus
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") saveEdit(a.id);
                        if (e.key === "Escape") setEditingId(null);
                      }}
                      className="w-32 rounded-md border border-border-strong bg-base px-2 py-0.5 text-body text-primary outline-none"
                    />
                  ) : (
                    <span className="text-body font-medium text-primary">{a.name}</span>
                  )}
                  <span
                    className={cn(
                      "rounded-badge border border-border-default bg-elevated px-1.5 py-0.5 text-badge text-secondary transition-opacity",
                      !editing && "group-hover:opacity-0",
                    )}
                  >
                    {a.currency}
                  </span>
                </div>
                <div className="tnum mt-3 text-mono-lg text-primary">
                  {formatMoney(a.balance, a.currency)}
                </div>
                {a.broker && <div className="mt-1 text-caption text-tertiary">{a.broker}</div>}

                {/* 操作行（hover 显示） */}
                {editing ? (
                  <div className="absolute right-4 top-3.5 flex gap-1">
                    <button
                      onClick={() => saveEdit(a.id)}
                      className="flex h-7 w-7 items-center justify-center rounded-md text-tertiary hover:bg-elevated hover:text-up"
                    >
                      <Check className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => setEditingId(null)}
                      className="flex h-7 w-7 items-center justify-center rounded-md text-tertiary hover:bg-elevated hover:text-primary"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ) : (
                  <div className="absolute right-3 top-3 flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                    <button
                      onClick={() => {
                        setEditingId(a.id);
                        setEditName(a.name);
                      }}
                      className="flex h-7 w-7 items-center justify-center rounded-md text-tertiary hover:bg-elevated hover:text-primary"
                      aria-label={t("cash.rename")}
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => onDelete(a.id)}
                      className="flex h-7 w-7 items-center justify-center rounded-md text-tertiary hover:bg-elevated hover:text-danger"
                      aria-label={t("cash.delete")}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                )}

                {/* hover 显示的两个主操作 */}
                {!editing && (
                  <div className="mt-4 flex gap-2 opacity-0 transition-opacity group-hover:opacity-100">
                    <Button size="sm" variant="secondary" className="flex-1 gap-1.5" onClick={() => setFlowAccount(a)}>
                      <PlusCircle className="h-3.5 w-3.5" />
                      {t("cash.recordFlowAction")}
                    </Button>
                    <Button size="sm" variant="outline" className="flex-1 gap-1.5" onClick={() => setFlowsAccount(a)}>
                      <ListOrdered className="h-3.5 w-3.5" />
                      {t("cash.flowsAction")}
                    </Button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* 新建账户弹窗 */}
      <NewAccountDialog open={newAccountOpen} onOpenChange={setNewAccountOpen} />

      {/* 记一笔弹窗 */}
      <RecordFlowDialog account={flowAccount} onClose={() => setFlowAccount(null)} />

      {/* 流水弹窗 */}
      <FlowsDialog account={flowsAccount} onClose={() => setFlowsAccount(null)} />
    </div>
  );
}

/** 现金总览：总额（可切币种）+ 各币种明细。 */
function CashOverview({
  summary,
  summaryCcy,
  onChangeCcy,
}: {
  summary: ReturnType<typeof useCashSummary>["data"];
  summaryCcy: string;
  onChangeCcy: (c: string) => void;
}) {
  const { t } = useT();
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
      {/* 总现金卡 */}
      <Card className="flex flex-col justify-between gap-4 p-5">
        <div className="flex items-center justify-between">
          <span className="label-caps">{t("cash.totalCash")}</span>
          <div className="flex gap-1 rounded-pill border border-border-default p-0.5">
            {CURRENCIES.map((c) => (
              <button
                key={c}
                onClick={() => onChangeCcy(c)}
                className={cn(
                  "rounded-pill px-2 py-0.5 text-caption font-medium transition-colors",
                  summaryCcy === c
                    ? "bg-elevated text-primary"
                    : "text-tertiary hover:text-primary",
                )}
              >
                {c}
              </button>
            ))}
          </div>
        </div>
        <div>
          <div className="tnum text-kpi text-primary">
            {formatMoney(summary?.total.amount ?? "0", summaryCcy)}
          </div>
          <p className="mt-1.5 text-caption text-tertiary">
            {t("cash.convertedAt")}
            {summary?.total.estimated && ` · ${t("cash.estimated")}`}
          </p>
        </div>
      </Card>

      {/* 各币种明细 */}
      <Card className="p-5 lg:col-span-2">
        <span className="label-caps">{t("cash.byCurrency")}</span>
        <div className="mt-3 grid gap-1.5">
          {(summary?.by_currency ?? []).length === 0 ? (
            <p className="py-4 text-center text-meta text-tertiary">—</p>
          ) : (
            (summary?.by_currency ?? []).map((row) => (
              <div
                key={row.currency}
                className="flex items-center justify-between rounded-lg px-3 py-2 hover:bg-elevated"
              >
                <div className="flex items-center gap-2.5">
                  <span className="tnum w-12 rounded-badge border border-border-default bg-elevated px-1.5 py-0.5 text-center text-badge text-secondary">
                    {row.currency}
                  </span>
                  <span className="tnum text-body text-primary">
                    {formatMoney(row.balance, row.currency)}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-caption text-tertiary">
                  {row.currency !== summaryCcy && row.rate && (
                    <span className="tnum hidden sm:inline">
                      {t("cash.rateAsOf", {
                        from: row.currency,
                        rate: Number(row.rate).toFixed(4),
                        to: summaryCcy,
                      })}
                    </span>
                  )}
                  <span className="tnum text-body text-secondary">
                    {row.converted != null ? formatMoney(row.converted, summaryCcy) : "—"}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
}

/** 新建账户弹窗。 */
function NewAccountDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const { t } = useT();
  const createAccount = useCreateAccount();
  const [name, setName] = useState("");
  const [ccy, setCcy] = useState("JPY");

  const submit = () => {
    if (!name.trim()) return;
    createAccount.mutate(
      { name: name.trim(), currency: ccy },
      {
        onSuccess: () => {
          setName("");
          setCcy("JPY");
          onOpenChange(false);
        },
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent title={t("cash.newAccountTitle")}>
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label>{t("cash.accName")}</Label>
            <Input
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
              placeholder={t("cash.accNamePlaceholder")}
            />
          </div>
          <div className="space-y-1.5">
            <Label>{t("cash.currency")}</Label>
            <Select value={ccy} onValueChange={setCcy} options={CCY_OPTIONS} />
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <DialogClose asChild>
              <Button variant="outline">{t("cash.cancel")}</Button>
            </DialogClose>
            <Button disabled={!name.trim() || createAccount.isPending} onClick={submit}>
              {t("cash.createAccount")}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/** 记一笔现金流弹窗。 */
function RecordFlowDialog({ account, onClose }: { account: CashAccount | null; onClose: () => void }) {
  const { t } = useT();
  const createFlow = useCreateCashFlow();
  const [flowType, setFlowType] = useState("DEPOSIT");
  const [amount, setAmount] = useState("");

  const FLOW_OPTIONS = ["DEPOSIT", "WITHDRAW", "DIVIDEND", "INTEREST"].map((ty) => ({
    value: ty,
    label: t(FLOW_TYPE_KEYS[ty]),
  }));

  const submit = () => {
    if (!account || !amount) return;
    const signed = flowType === "WITHDRAW" && !amount.startsWith("-") ? `-${amount}` : amount;
    createFlow.mutate(
      { account_id: account.id, type: flowType, amount: signed },
      {
        onSuccess: () => {
          setAmount("");
          setFlowType("DEPOSIT");
          onClose();
        },
      },
    );
  };

  return (
    <Dialog open={account != null} onOpenChange={(o) => !o && onClose()}>
      <DialogContent title={account ? t("cash.recordFlowTitle", { name: account.name }) : ""}>
        {account && (
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label>{t("cash.flowType")}</Label>
              <Select value={flowType} onValueChange={setFlowType} options={FLOW_OPTIONS} />
            </div>
            <div className="space-y-1.5">
              <Label>{t("cash.amount", { currency: account.currency })}</Label>
              <Input
                autoFocus
                className="tnum"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && submit()}
                placeholder={t("cash.amountPlaceholder")}
              />
            </div>
            <div className="flex justify-end gap-2 pt-1">
              <DialogClose asChild>
                <Button variant="outline">{t("cash.cancel")}</Button>
              </DialogClose>
              <Button disabled={!amount || createFlow.isPending} onClick={submit}>
                {t("cash.recordTo", { name: account.name })}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

/** 账户流水弹窗。 */
function FlowsDialog({ account, onClose }: { account: CashAccount | null; onClose: () => void }) {
  const { t } = useT();
  const { data: flows } = useCashFlows(account?.id);

  return (
    <Dialog open={account != null} onOpenChange={(o) => !o && onClose()}>
      <DialogContent
        title={account ? t("cash.flowsTitle", { name: account.name }) : ""}
        className="max-w-lg"
      >
        <div className="max-h-[60vh] overflow-y-auto">
          <div className="grid grid-cols-[1fr_1fr_1fr] items-center gap-4 border-b border-border-default pb-2 label-caps">
            <div>{t("cash.col.date")}</div>
            <div>{t("cash.col.type")}</div>
            <div className="text-right">{t("cash.col.amount")}</div>
          </div>
          {!flows || flows.length === 0 ? (
            <div className="py-10 text-center text-tertiary">{t("cash.noFlows")}</div>
          ) : (
            flows.map((f) => {
              const amt = Number(f.amount);
              return (
                <div
                  key={f.id}
                  className="grid grid-cols-[1fr_1fr_1fr] items-center gap-4 border-b border-border-default py-2.5 last:border-b-0"
                >
                  <div className="tnum text-secondary">{formatDate(f.flow_date)}</div>
                  <div className="text-primary">
                    {FLOW_TYPE_KEYS[f.type] ? t(FLOW_TYPE_KEYS[f.type]) : f.type}
                  </div>
                  <div className={cn("tnum text-right", amt >= 0 ? "text-up" : "text-down")}>
                    {formatMoney(f.amount, f.currency, { sign: true })}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
