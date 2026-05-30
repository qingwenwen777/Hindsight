"use client";

import { Plus, Sparkles, Trash2, X } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useT } from "@/lib/i18n/use-t";
import {
  type ScreenCondition,
  type ScreenHit,
  useDeleteRule,
  useReviewScreen,
  useRunScreen,
  useSaveRule,
  useScreenerFields,
  useScreenerRules,
} from "@/lib/hooks/use-screener";
import { cn } from "@/lib/utils";

const NUMERIC = new Set([
  "pe", "pb", "roe", "revenue_yoy", "profit_yoy", "dividend_yield", "eps", "market_cap",
]);
const BOOL = new Set(["in_watchlist", "in_holdings", "is_etf"]);
const MARKETS = ["US", "CN", "HK", "JP"];

export default function ScreenerPage() {
  const { t } = useT();
  const { data: fieldsData } = useScreenerFields();
  const { data: rules } = useScreenerRules();
  const run = useRunScreen();
  const saveRule = useSaveRule();
  const delRule = useDeleteRule();
  const review = useReviewScreen();

  const fields = fieldsData?.fields ?? [];
  const ops = fieldsData?.operators ?? ["<", "<=", ">", ">=", "=", "between"];

  const [conditions, setConditions] = useState<ScreenCondition[]>([
    { field: "pe", op: "<", value: "20" },
  ]);
  const [markets, setMarkets] = useState<string[]>([]);
  const [hits, setHits] = useState<ScreenHit[] | null>(null);
  const [ruleName, setRuleName] = useState("");
  const [reviewMsg, setReviewMsg] = useState<string | null>(null);

  const addCondition = () => setConditions((c) => [...c, { field: "pe", op: "<", value: "" }]);
  const removeCondition = (i: number) => setConditions((c) => c.filter((_, idx) => idx !== i));
  const updateCondition = (i: number, patch: Partial<ScreenCondition>) =>
    setConditions((c) => c.map((cond, idx) => (idx === i ? { ...cond, ...patch } : cond)));

  const toggleMarket = (m: string) =>
    setMarkets((prev) => (prev.includes(m) ? prev.filter((x) => x !== m) : [...prev, m]));

  const onRun = () => {
    setReviewMsg(null);
    run.mutate(
      { conditions, markets: markets.length ? markets : null },
      { onSuccess: (data) => setHits(data) },
    );
  };

  const onReview = () => {
    review.mutate(
      { conditions, markets: markets.length ? markets : null, rule_name: ruleName || undefined },
      { onSuccess: () => setReviewMsg(t("screener.reviewQueued")) },
    );
  };

  const fieldLabel = (f: string) => {
    const key = `screener.field.${f}`;
    const lbl = t(key);
    return lbl === key ? f : lbl;
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-display text-secondary">{t("screener.title")}</h1>
        <p className="mt-2 text-meta text-tertiary">{t("screener.subtitle")}</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t("screener.conditions")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {conditions.map((cond, i) => {
            const isBool = BOOL.has(cond.field);
            const isNum = NUMERIC.has(cond.field);
            return (
              <div key={i} className="flex flex-wrap items-center gap-2">
                <Select
                  value={cond.field}
                  onValueChange={(v) => updateCondition(i, { field: v })}
                  options={fields.map((f) => ({ value: f, label: fieldLabel(f) }))}
                  className="w-40"
                />

                {!isBool && (
                  <Select
                    value={cond.op}
                    onValueChange={(v) => updateCondition(i, { op: v })}
                    options={(isNum ? ops : ["="]).map((o) => ({ value: o, label: o }))}
                    className="w-24"
                  />
                )}

                {isBool ? (
                  <Select
                    value={String(cond.value ?? true)}
                    onValueChange={(v) => updateCondition(i, { op: "=", value: v === "true" })}
                    options={[
                      { value: "true", label: t("screener.yes") },
                      { value: "false", label: t("screener.no") },
                    ]}
                    className="w-24"
                  />
                ) : (
                  <Input
                    className="w-28"
                    value={cond.value == null ? "" : String(cond.value)}
                    onChange={(e) => updateCondition(i, { value: e.target.value })}
                    placeholder={t("screener.value")}
                  />
                )}
                {!isBool && cond.op === "between" && (
                  <Input
                    className="w-28"
                    value={cond.value2 == null ? "" : String(cond.value2)}
                    onChange={(e) => updateCondition(i, { value2: e.target.value })}
                    placeholder={t("screener.value2")}
                  />
                )}

                <button
                  onClick={() => removeCondition(i)}
                  className="flex h-8 w-8 items-center justify-center rounded-md text-tertiary hover:bg-elevated hover:text-danger"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            );
          })}

          <Button variant="outline" size="sm" onClick={addCondition}>
            <Plus className="h-3.5 w-3.5" /> {t("screener.addCondition")}
          </Button>

          <div className="flex items-center gap-2 pt-1">
            <span className="text-meta text-tertiary">{t("screener.markets")}：</span>
            {MARKETS.map((m) => (
              <Button key={m} size="sm" variant={markets.includes(m) ? "default" : "outline"} onClick={() => toggleMarket(m)}>
                {m}
              </Button>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-2 pt-2">
            <Button disabled={run.isPending} onClick={onRun}>
              {run.isPending ? t("screener.running") : t("screener.run")}
            </Button>
            <Input
              className="w-40"
              value={ruleName}
              onChange={(e) => setRuleName(e.target.value)}
              placeholder={t("screener.ruleName")}
            />
            <Button
              variant="outline"
              disabled={!ruleName || saveRule.isPending}
              onClick={() => saveRule.mutate({ name: ruleName, conditions, markets: markets.length ? markets : null })}
            >
              {t("screener.saveRule")}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 已存规则 */}
      {(rules ?? []).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>{t("screener.savedRules")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            {(rules ?? []).map((r) => (
              <div key={r.id} className="flex items-center justify-between rounded-md px-2 py-1.5 hover:bg-elevated">
                <span className="text-body text-primary">{r.name}</span>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setConditions(r.conditions);
                      setMarkets(r.markets ?? []);
                      setRuleName(r.name);
                    }}
                  >
                    {t("screener.load")}
                  </Button>
                  <button
                    onClick={() => delRule.mutate(r.id)}
                    className="flex h-8 w-8 items-center justify-center rounded-md text-tertiary hover:bg-base hover:text-danger"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* 结果 */}
      {hits !== null && (
        <Card className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-border-default px-5 py-3">
            <span className="text-title font-medium text-primary">
              {t("screener.results")} · {t("screener.hits", { n: hits.length })}
            </span>
            {hits.length > 0 && (
              <Button size="sm" variant="secondary" disabled={review.isPending} onClick={onReview}>
                <Sparkles className="h-3.5 w-3.5" />
                {review.isPending ? t("screener.reviewing") : t("screener.review")}
              </Button>
            )}
          </div>
          {reviewMsg && (
            <div className="border-b border-border-default bg-elevated/40 px-5 py-2 text-meta text-up">
              {reviewMsg} · <Link href="/insights" className="underline">{t("insights.title")}</Link>
            </div>
          )}
          {hits.length === 0 ? (
            <div className="px-5 py-10 text-center text-tertiary">{t("screener.noHits")}</div>
          ) : (
            hits.map((h) => (
              <div key={h.stock_id} className="border-b border-border-default px-5 py-3 last:border-b-0">
                <div className="flex items-center justify-between">
                  <Link href={`/stocks/${h.stock_id}`} className="text-primary hover:text-accent">
                    {h.name} <span className="tnum text-tertiary">{h.symbol} · {h.market}</span>
                  </Link>
                </div>
                <div className="mt-1 flex flex-wrap gap-2 text-caption text-secondary">
                  {Object.entries(h.matched).map(([k, v]) => (
                    <span key={k} className="rounded-badge border border-border-default px-1.5 py-0.5">
                      {fieldLabel(k)}: {v}
                    </span>
                  ))}
                  {h.missing.map((m) => (
                    <span key={m} className="rounded-badge border border-warn/40 px-1.5 py-0.5 text-warn">
                      {fieldLabel(m)} {t("screener.missing")}
                    </span>
                  ))}
                </div>
              </div>
            ))
          )}
          <div className="px-5 py-2.5 text-caption text-muted">{t("screener.disclaimer")}</div>
        </Card>
      )}
    </div>
  );
}
