"use client";

import { useParams } from "next/navigation";
import { useState } from "react";

import { CandleChart } from "@/components/charts/candle-chart";
import { IndicatorPanel } from "@/components/charts/indicator-panel";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  useIndicators,
  usePrices,
  useStock,
  useStockTransactions,
} from "@/lib/hooks/use-stock";

export default function StockDetailPage() {
  const params = useParams();
  const id = Number(params.id);
  const { data: stock } = useStock(id);
  const { data: prices, isLoading: pricesLoading } = usePrices(id);
  const { data: indicators } = useIndicators(id);
  const { data: txs } = useStockTransactions(id);

  const [subPanel, setSubPanel] = useState<"MACD" | "RSI">("MACD");

  return (
    <div className="space-y-6">
      {/* 头部 */}
      <div className="flex items-center gap-3">
        <h1 className="text-h1 text-primary">{stock?.name ?? "…"}</h1>
        <span className="tnum rounded-sm bg-elevated px-2 py-1 text-small text-secondary">
          {stock?.symbol}
        </span>
        {stock && (
          <span className="rounded-sm bg-accent/10 px-2 py-1 text-caption text-accent">
            {stock.market}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        {/* 主图 + 副图 */}
        <div className="space-y-4 lg:col-span-3">
          <Card>
            <CardHeader>
              <CardTitle>K 线（叠加 MA / 布林带 + 买卖点）</CardTitle>
            </CardHeader>
            <CardContent>
              {pricesLoading ? (
                <div className="h-[480px] animate-pulse rounded-md bg-elevated" />
              ) : (
                <CandleChart prices={prices ?? []} indicators={indicators} transactions={txs ?? []} />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>副图</CardTitle>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant={subPanel === "MACD" ? "default" : "outline"}
                  onClick={() => setSubPanel("MACD")}
                >
                  MACD
                </Button>
                <Button
                  size="sm"
                  variant={subPanel === "RSI" ? "default" : "outline"}
                  onClick={() => setSubPanel("RSI")}
                >
                  RSI
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {indicators ? (
                <IndicatorPanel indicators={indicators} type={subPanel} />
              ) : (
                <div className="h-[140px] animate-pulse rounded-md bg-elevated" />
              )}
            </CardContent>
          </Card>
        </div>

        {/* 右侧栏 */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>关联交易</CardTitle>
            </CardHeader>
            <CardContent>
              {!txs || txs.length === 0 ? (
                <p className="text-small text-secondary">无关联交易</p>
              ) : (
                <div className="space-y-2">
                  {txs.map((t) => (
                    <div key={t.id} className="flex items-center justify-between text-small">
                      <span className={t.type === "BUY" ? "text-up" : "text-down"}>
                        {t.type === "BUY" ? "买" : "卖"} {Number(t.quantity)}
                      </span>
                      <span className="tnum text-secondary">{t.trade_date}</span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>AI 洞察</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-small text-secondary">AI 复盘将在 Phase 4 接入。</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
