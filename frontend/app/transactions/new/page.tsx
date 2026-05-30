"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { ConcentrationAlert } from "@/components/forms/concentration-alert";
import { ConfidenceSlider } from "@/components/forms/confidence-slider";
import { CooldownButton } from "@/components/forms/cooldown-button";
import { EmotionPicker } from "@/components/forms/emotion-picker";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api/client";
import { formatMoney } from "@/lib/format";
import { useCooldownCheck } from "@/lib/hooks/use-biases";
import {
  useCreateStock,
  useCreateTransaction,
  useStockDiscover,
  useStockSearch,
} from "@/lib/hooks/use-portfolio";
import type { DiscoverCandidate, Stock, TransactionCreate } from "@/lib/api/types";

const MIN_THESIS = 100;

export default function NewTransactionPage() {
  const router = useRouter();
  const createTx = useCreateTransaction();
  const cooldownCheck = useCooldownCheck();

  const [step, setStep] = useState<1 | 2>(1);
  const [error, setError] = useState<string | null>(null);
  const [defenseWarnings, setDefenseWarnings] = useState<string[]>([]);
  const [cooldownSeconds, setCooldownSeconds] = useState(30);
  const [requireAiConfirm, setRequireAiConfirm] = useState(false);

  // Step 1 — 交易信息
  const [stock, setStock] = useState<Stock | null>(null);
  const [search, setSearch] = useState("");
  const { data: searchResults } = useStockSearch(search);
  const localEmpty = search.trim().length >= 2 && (searchResults ?? []).length === 0;
  const { data: discovered, isFetching: discovering } = useStockDiscover(search, localEmpty);
  const createStock = useCreateStock();
  const [adding, setAdding] = useState<string | null>(null);
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [tradeDate, setTradeDate] = useState(() => new Date().toISOString().slice(0, 10));

  // Step 2 — 决策日志
  const [decisionType, setDecisionType] = useState("BUY");
  const [thesisCategory, setThesisCategory] = useState("GROWTH");
  const [horizon, setHorizon] = useState("MEDIUM");
  const [targetPrice, setTargetPrice] = useState("");
  const [stopLoss, setStopLoss] = useState("");
  const [exitCondition, setExitCondition] = useState("");
  const [confidence, setConfidence] = useState<number | undefined>();
  const [emotion, setEmotion] = useState<string | undefined>();
  const [thesis, setThesis] = useState("");
  const [risks, setRisks] = useState("");

  const amount = useMemo(() => {
    const q = Number(quantity);
    const p = Number(price);
    if (Number.isNaN(q) || Number.isNaN(p)) return 0;
    return q * p;
  }, [quantity, price]);

  const step1Valid = stock && Number(quantity) > 0 && Number(price) > 0;
  const thesisValid = thesis.trim().length >= MIN_THESIS;
  const step2Valid = thesisValid && decisionType;

  // 一键登记候选股票（含后台同步行情）并选中
  const addCandidate = (c: DiscoverCandidate) => {
    const key = `${c.market}:${c.symbol}`;
    setAdding(key);
    createStock.mutate(
      {
        symbol: c.symbol,
        market: c.market,
        name: c.name,
        currency: c.currency,
        is_etf: c.quote_type === "ETF",
        sync: true,
      },
      {
        onSuccess: (s) => {
          setStock(s);
          setSearch("");
          setAdding(null);
        },
        onError: () => setAdding(null),
      },
    );
  };

  const submit = () => {
    if (!stock) return;
    setError(null);
    const payload: TransactionCreate = {
      stock_id: stock.id,
      type: side,
      trade_date: tradeDate,
      quantity,
      price,
      currency: stock.currency,
      journal: {
        decision_type: decisionType,
        thesis_category: thesisCategory,
        expected_horizon: horizon,
        target_price: targetPrice || undefined,
        stop_loss_price: stopLoss || undefined,
        exit_condition: exitCondition || undefined,
        confidence,
        emotion,
        thesis,
        risks: risks || undefined,
      },
    };
    createTx.mutate(payload, {
      onSuccess: () => router.push("/"),
      onError: (e) => setError(e instanceof ApiError ? e.message : "提交失败，请重试"),
    });
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-h1 text-primary">录入交易</h1>
        <p className="text-small text-secondary">
          每笔交易强制关联决策日志，提交前有 30 秒冷静期。
        </p>
      </div>

      {/* 步骤指示 */}
      <div className="flex items-center gap-2 text-small">
        <span className={step === 1 ? "text-accent" : "text-secondary"}>① 交易信息</span>
        <span className="text-muted">→</span>
        <span className={step === 2 ? "text-accent" : "text-secondary"}>② 决策日志</span>
      </div>

      {step === 1 && (
        <Card>
          <CardHeader>
            <CardTitle>交易信息</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* 股票搜索 */}
            <div className="space-y-1">
              <Label>股票</Label>
              {stock ? (
                <div className="flex items-center justify-between rounded-md border border-border-subtle bg-base px-3 py-2">
                  <span className="text-small text-primary">
                    {stock.name} <span className="tnum text-secondary">({stock.symbol})</span>
                  </span>
                  <Button variant="ghost" size="sm" onClick={() => setStock(null)}>
                    更换
                  </Button>
                </div>
              ) : (
                <div className="relative">
                  <Input
                    placeholder="输入代码或名称搜索…"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                  {searchResults && searchResults.length > 0 && (
                    <div className="absolute z-10 mt-1 w-full rounded-md border border-border-subtle bg-elevated shadow-lg">
                      {searchResults.map((s) => (
                        <button
                          key={s.id}
                          type="button"
                          onClick={() => {
                            setStock(s);
                            setSearch("");
                          }}
                          className="flex w-full items-center justify-between px-3 py-2 text-left text-small text-primary hover:bg-surface"
                        >
                          <span>{s.name}</span>
                          <span className="tnum text-secondary">{s.symbol} · {s.market}</span>
                        </button>
                      ))}
                    </div>
                  )}
                  {/* 本地无结果 → 数据源发现 */}
                  {localEmpty && (
                    <div className="absolute z-10 mt-1 w-full rounded-md border border-border-subtle bg-elevated shadow-lg">
                      {(discovered ?? []).length > 0 && (
                        <p className="px-3 pt-2 text-caption text-tertiary">
                          本地未登记，从数据源发现：
                        </p>
                      )}
                      {(discovered ?? []).map((c) => {
                        const key = `${c.market}:${c.symbol}`;
                        return (
                          <button
                            key={key}
                            type="button"
                            disabled={adding === key}
                            onClick={() => addCandidate(c)}
                            className="flex w-full items-center justify-between px-3 py-2 text-left text-small text-primary hover:bg-surface disabled:opacity-60"
                          >
                            <span>{c.name}</span>
                            <span className="tnum text-secondary">
                              {adding === key ? "添加中…" : `${c.symbol} · ${c.market}`}
                            </span>
                          </button>
                        );
                      })}
                      {(discovered ?? []).length === 0 && (
                        <p className="px-3 py-2 text-small text-tertiary">
                          {discovering ? "正在从数据源搜索…" : "未找到匹配股票。"}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* 方向 */}
            <div className="space-y-1">
              <Label>方向</Label>
              <div className="flex gap-2">
                <Button
                  variant={side === "BUY" ? "up" : "outline"}
                  onClick={() => setSide("BUY")}
                >
                  买入
                </Button>
                <Button
                  variant={side === "SELL" ? "down" : "outline"}
                  onClick={() => setSide("SELL")}
                >
                  卖出
                </Button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <Label>数量</Label>
                <Input
                  type="number"
                  className="tnum"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label>价格</Label>
                <Input
                  type="number"
                  className="tnum"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-1">
              <Label>交易日期</Label>
              <Input
                type="date"
                className="tnum"
                value={tradeDate}
                onChange={(e) => setTradeDate(e.target.value)}
              />
            </div>

            {/* 预览 */}
            <div className="rounded-md border border-border-subtle bg-base p-3 text-small">
              <div className="flex justify-between">
                <span className="text-secondary">预估成交额</span>
                <span className="tnum text-primary">
                  {stock ? formatMoney(amount, stock.currency) : "—"}
                </span>
              </div>
              <p className="mt-2 text-caption text-muted">手续费将在提交时由后端按市场规则自动计算。</p>
            </div>

            <div className="flex justify-end">
              <Button
                disabled={!step1Valid || cooldownCheck.isPending}
                onClick={() => {
                  if (!stock) return;
                  // 录入前防御检测
                  cooldownCheck.mutate(
                    { stock_id: stock.id, type: side, sell_date: tradeDate },
                    {
                      onSuccess: (res) => {
                        setDefenseWarnings(res.warnings || []);
                        setCooldownSeconds(res.cooldown_seconds || 30);
                        setRequireAiConfirm(res.require_ai_confirm || false);
                        setStep(2);
                      },
                      onError: () => {
                        // 检测失败不阻断录入，用默认冷静期
                        setCooldownSeconds(30);
                        setStep(2);
                      },
                    },
                  );
                }}
              >
                {cooldownCheck.isPending ? "检测中…" : "下一步：决策日志"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {step === 2 && (
        <Card>
          <CardHeader>
            <CardTitle>决策日志（全部必填核心字段）</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* 防御告警（复仇交易 / 持有时间） */}
            <ConcentrationAlert warnings={defenseWarnings} />
            {requireAiConfirm && (
              <p className="text-small text-warn">
                检测到疑似复仇交易，冷静期已延长至 {Math.round(cooldownSeconds / 60)} 分钟，建议先用 AI 复盘确认。
              </p>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <Label>决策类型</Label>
                <Select
                  value={decisionType}
                  onValueChange={setDecisionType}
                  options={["BUY", "SELL", "HOLD", "WATCH"].map((v) => ({ value: v, label: v }))}
                />
              </div>
              <div className="space-y-1">
                <Label>论点类别</Label>
                <Select
                  value={thesisCategory}
                  onValueChange={setThesisCategory}
                  options={["VALUATION", "TREND", "EVENT", "GROWTH", "OTHER"].map((v) => ({ value: v, label: v }))}
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-1">
                <Label>预期持有</Label>
                <Select
                  value={horizon}
                  onValueChange={setHorizon}
                  options={["SHORT", "MEDIUM", "LONG"].map((v) => ({ value: v, label: v }))}
                />
              </div>
              <div className="space-y-1">
                <Label>目标价</Label>
                <Input className="tnum" value={targetPrice} onChange={(e) => setTargetPrice(e.target.value)} />
              </div>
              <div className="space-y-1">
                <Label>止损价</Label>
                <Input className="tnum" value={stopLoss} onChange={(e) => setStopLoss(e.target.value)} />
              </div>
            </div>

            <div className="space-y-1">
              <Label>退出条件</Label>
              <Input value={exitCondition} onChange={(e) => setExitCondition(e.target.value)} />
            </div>

            <div className="space-y-1">
              <Label>信心评分</Label>
              <ConfidenceSlider value={confidence} onChange={setConfidence} />
            </div>

            <div className="space-y-1">
              <Label>当前情绪</Label>
              <EmotionPicker value={emotion} onChange={setEmotion} />
            </div>

            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <Label>投资逻辑（≥ {MIN_THESIS} 字）</Label>
                <span className={`text-caption ${thesisValid ? "text-up" : "text-muted"}`}>
                  {thesis.trim().length}/{MIN_THESIS}
                </span>
              </div>
              <Textarea
                rows={5}
                value={thesis}
                onChange={(e) => setThesis(e.target.value)}
                placeholder="为什么做这笔交易？逻辑、催化剂、估值依据…"
              />
            </div>

            <div className="space-y-1">
              <Label>主要风险</Label>
              <Textarea rows={2} value={risks} onChange={(e) => setRisks(e.target.value)} />
            </div>

            {error && <p className="text-small text-danger">{error}</p>}

            <div className="flex items-center justify-between">
              <Button variant="ghost" onClick={() => setStep(1)}>
                上一步
              </Button>
              <CooldownButton
                seconds={cooldownSeconds}
                disabled={!step2Valid}
                loading={createTx.isPending}
                onConfirm={submit}
              />
            </div>
            {!thesisValid && (
              <p className="text-caption text-muted">投资逻辑需至少 {MIN_THESIS} 字才能提交。</p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
