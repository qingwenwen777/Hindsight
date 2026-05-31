"use client";

import { useQuery } from "@tanstack/react-query";
import { Star } from "lucide-react";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";

import { CandleChart } from "@/components/charts/candle-chart";
import { IndicatorPanel } from "@/components/charts/indicator-panel";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api/client";
import { formatMoney, formatQuantity, pnlDirection } from "@/lib/format";
import { useT } from "@/lib/i18n/use-t";
import { cn } from "@/lib/utils";
import {
  useFinancials,
  useIndicators,
  usePrices,
  useStock,
  useStockTransactions,
} from "@/lib/hooks/use-stock";
import { useAddWatch, useRemoveWatch, useWatchlist } from "@/lib/hooks/use-watchlist";
import type { Holding, Journal } from "@/lib/api/types";

const RANGES = ["1M", "3M", "6M", "1Y", "All"] as const;

export default function StockDetailPage() {
  const { t } = useT();
  const params = useParams();
  const id = Number(params.id);
  const { data: stock } = useStock(id);
  const { data: prices, isLoading: pricesLoading } = usePrices(id);
  const { data: indicators } = useIndicators(id);
  const { data: txs } = useStockTransactions(id);
  const { data: financials } = useFinancials(id);

  const [range, setRange] = useState<(typeof RANGES)[number]>("3M");
  const [subPanel, setSubPanel] = useState<"MACD" | "RSI">("MACD");

  // 该股持仓摘要
  const { data: holdings } = useQuery({
    queryKey: ["holdings"],
    queryFn: async () => (await api.get<Holding[]>("/portfolio/holdings")).data,
  });
  const holding = holdings?.find((h) => h.stock_id === id);

  // 关联日志（取目标价/止损价画线）
  const { data: journals } = useQuery({
    queryKey: ["journals", id],
    queryFn: async () => (await api.get<Journal[]>(`/journals?stock_id=${id}`)).data,
    enabled: Number.isFinite(id),
  });

  // 关注状态
  const { data: watch } = useWatchlist();
  const addWatch = useAddWatch();
  const removeWatch = useRemoveWatch();
  const isWatched = (watch ?? []).some((w) => w.stock_id === id);

  const lastClose = prices && prices.length > 0 ? Number(prices[prices.length - 1].close) : null;
  const prevClose = prices && prices.length > 1 ? Number(prices[prices.length - 2].close) : null;
  const dayChange = lastClose != null && prevClose != null ? lastClose - prevClose : null;
  const dayChangePct = dayChange != null && prevClose ? (dayChange / prevClose) * 100 : null;

  // 范围裁剪
  const rangedPrices = useMemo(() => {
    if (!prices) return [];
    const days: Record<string, number> = { "1M": 22, "3M": 66, "6M": 132, "1Y": 252, All: 1e9 };
    const n = days[range];
    return prices.slice(-n);
  }, [prices, range]);

  // 目标价/止损价线
  const priceLines = useMemo(() => {
    const latest = (journals ?? []).find((j) => j.target_price || j.stop_loss_price);
    const lines: { price: number; color: string; title: string }[] = [];
    if (latest?.target_price) lines.push({ price: Number(latest.target_price), color: "#d9a441", title: t("stock.target", { price: latest.target_price }) });
    if (latest?.stop_loss_price) lines.push({ price: Number(latest.stop_loss_price), color: "#f05b5b", title: t("stock.stop", { price: latest.stop_loss_price }) });
    return lines;
  }, [journals, t]);

  const dir = pnlDirection(dayChange);

  return (
    <div>
      {/* 头部 */}
      <header className="grid grid-cols-1 items-start gap-4 border-b border-border-default pb-5 sm:grid-cols-[1fr_auto]">
          <div>
            <div className="flex flex-wrap items-baseline gap-2.5">
              <h1 className="text-display text-primary">{stock?.symbol ?? "…"}</h1>
              <span className="text-meta text-tertiary">{stock?.name}</span>
              {stock && (
                <span className="rounded-badge border border-border-default bg-elevated px-1.5 py-0.5 text-badge font-medium text-secondary">
                  {stock.market}
                </span>
              )}
            </div>
            <p className="mt-2 text-meta text-tertiary">{t("stock.linkedView")}</p>
          </div>
          <div className="text-left sm:text-right">
            <div className="tnum text-kpi text-primary">
              {lastClose != null ? formatMoney(lastClose, stock?.currency ?? "USD") : "—"}
            </div>
            {dayChange != null && (
              <div className={cn("tnum mt-2 text-body", dir === "up" ? "text-up" : dir === "down" ? "text-down" : "text-tertiary")}>
                {dayChange >= 0 ? "+" : ""}
                {dayChange.toFixed(2)} ({dayChangePct?.toFixed(2)}%)
              </div>
            )}
            <div className="mt-2 flex justify-start sm:justify-end">
              <Button
                size="sm"
                variant={isWatched ? "secondary" : "outline"}
                onClick={() =>
                  isWatched ? removeWatch.mutate(id) : addWatch.mutate({ stock_id: id })
                }
              >
                <Star className={cn("h-3.5 w-3.5", isWatched && "fill-current text-warn")} />
                {isWatched ? t("stock.watched") : t("stock.watch")}
              </Button>
            </div>
          </div>
        </header>

        {/* 快速指标条 */}
        <div className="grid grid-cols-2 gap-px bg-border-subtle sm:grid-cols-5">
          <Metric label={t("stock.cost")} value={holding ? formatMoney(holding.avg_cost, holding.currency) : "—"} />
          <Metric label={t("stock.shares")} value={holding ? formatQuantity(holding.shares) : "—"} />
          <Metric
            label={t("stock.marketValue")}
            value={holding ? formatMoney(holding.market_value ?? holding.cost_basis, holding.currency) : "—"}
          />
          <Metric
            label={t("stock.unrealizedPnl")}
            value={holding && holding.unrealized_pnl != null ? formatMoney(holding.unrealized_pnl, holding.currency, { sign: true }) : "—"}
            direction={holding ? pnlDirection(holding.unrealized_pnl) : "flat"}
          />
          <Metric label={t("stock.realizedPnl")} value={holding ? formatMoney(holding.realized_pnl, holding.currency, { sign: true }) : "—"} direction={holding ? pnlDirection(holding.realized_pnl) : "flat"} />
        </div>

        {/* 财务/估值 */}
        <div className="grid grid-cols-2 gap-px border-b border-border-subtle bg-border-subtle sm:grid-cols-4 lg:grid-cols-7">
          <Metric label="PE" value={fmtRatio(financials?.pe)} />
          <Metric label="PB" value={fmtRatio(financials?.pb)} />
          <Metric label="ROE(TTM)" value={fmtPct(financials?.roe)} />
          <Metric label={t("stock.revenueYoy")} value={fmtPct(financials?.revenue_yoy)} direction={dirOf(financials?.revenue_yoy)} />
          <Metric label={t("stock.profitYoy")} value={fmtPct(financials?.profit_yoy)} direction={dirOf(financials?.profit_yoy)} />
          <Metric label="EPS" value={fmtRatio(financials?.eps)} />
          <Metric label={t("stock.dividendYield")} value={fmtPct(financials?.dividend_yield)} />
        </div>

        {/* 主图 */}
        <div className="pt-6">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-title font-medium text-primary">{t("stock.priceAction")}</h2>
            <div className="flex gap-1.5">
              {RANGES.map((r) => (
                <button
                  key={r}
                  onClick={() => setRange(r)}
                  className={cn(
                    "flex h-7 min-w-[34px] items-center justify-center rounded-md border border-border-default text-caption font-medium",
                    range === r ? "bg-elevated text-primary" : "text-tertiary hover:text-primary",
                  )}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>
          <div className="overflow-hidden rounded-lg border border-border-default bg-base">
            {pricesLoading ? (
              <div className="skeleton h-[450px]" />
            ) : (
              <CandleChart
                prices={rangedPrices}
                indicators={indicators}
                transactions={txs ?? []}
                priceLines={priceLines}
              />
            )}
          </div>

          {/* 副图 */}
          <div className="mt-3 flex items-center justify-between">
            <h2 className="text-title font-medium text-primary">{t("stock.subPanel")}</h2>
            <div className="flex gap-1.5">
              {(["MACD", "RSI"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setSubPanel(t)}
                  className={cn(
                    "flex h-7 min-w-[44px] items-center justify-center rounded-md border border-border-default text-caption font-medium",
                    subPanel === t ? "bg-elevated text-primary" : "text-tertiary hover:text-primary",
                  )}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
          <div className="mt-3 overflow-hidden rounded-lg border border-border-default bg-base">
            {indicators ? (
              <IndicatorPanel indicators={indicators} type={subPanel} />
            ) : (
              <div className="skeleton h-[140px]" />
            )}
          </div>

          {/* 决策日志 rail */}
          <div className="mt-4 flex gap-3 overflow-x-auto pb-1">
            {(txs ?? []).length === 0 ? (
              <p className="text-meta text-tertiary">{t("stock.noLinkedTx")}</p>
            ) : (
              (txs ?? []).map((tx) => (
                <div
                  key={tx.id}
                  className="min-w-[300px] rounded-lg border border-border-default bg-base p-4"
                >
                  <div className="flex items-center justify-between">
                    <span
                      className={cn(
                        "rounded-badge border border-border-default bg-elevated px-1.5 py-0.5 text-badge font-medium",
                        tx.type === "BUY" ? "text-up" : "text-down",
                      )}
                    >
                      {tx.type}
                    </span>
                    <span className="tnum text-meta text-tertiary">
                      {tx.trade_date} @ {Number(tx.price)}
                    </span>
                  </div>
                  <div className="mt-3 grid grid-cols-2 gap-2.5">
                    <Mini label={t("stock.qty")} value={formatQuantity(tx.quantity)} />
                    <Mini label={t("stock.amount")} value={formatMoney(Number(tx.quantity) * Number(tx.price), tx.currency)} />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
    </div>
  );
}

function fmtRatio(v: string | null | undefined): string {
  if (!v) return "—";
  const n = Number(v);
  return Number.isNaN(n) ? "—" : n.toFixed(2);
}

function fmtPct(v: string | null | undefined): string {
  if (!v) return "—";
  const n = Number(v);
  return Number.isNaN(n) ? "—" : `${(n * 100).toFixed(1)}%`;
}

function dirOf(v: string | null | undefined): "up" | "down" | "flat" {
  if (!v) return "flat";
  const n = Number(v);
  if (Number.isNaN(n) || n === 0) return "flat";
  return n > 0 ? "up" : "down";
}

function Metric({ label, value, direction = "flat" }: { label: string; value: string; direction?: "up" | "down" | "flat" }) {
  const color = direction === "up" ? "text-up" : direction === "down" ? "text-down" : "text-primary";
  return (
    <div className="bg-surface px-5 py-3.5">
      <div className="label-caps">{label}</div>
      <div className={cn("tnum mt-2 font-medium", color)}>{value}</div>
    </div>
  );
}

function Mini({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-caption text-tertiary">{label}</div>
      <div className="tnum mt-0.5 font-medium text-secondary">{value}</div>
    </div>
  );
}
