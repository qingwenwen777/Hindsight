"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { Stat } from "@/components/stats/stat";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api/client";
import { formatPercent, pnlDirection } from "@/lib/format";

const MARKETS = ["US", "CN", "HK", "JP"];

export default function BenchmarkPage() {
  const [market, setMarket] = useState("US");
  const { data } = useQuery({
    queryKey: ["benchmark", market],
    queryFn: async () =>
      (await api.get<any>(`/portfolio/benchmark-comparison?benchmark_market=${market}`)).data,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-h1 text-primary">基准对比</h1>
          <p className="text-small text-secondary">组合 vs 基准的 alpha / 信息比率 / 跟踪误差 / β。</p>
        </div>
        <div className="flex gap-2">
          {MARKETS.map((m) => (
            <Button key={m} size="sm" variant={market === m ? "default" : "outline"} onClick={() => setMarket(m)}>
              {m}
            </Button>
          ))}
        </div>
      </div>

      {!data?.available ? (
        <Card>
          <CardContent className="p-8 text-center text-secondary">
            {data?.message ?? "加载中…"}
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <Stat label="组合收益" value={formatPercent((data.portfolio_return ?? 0) * 100, { sign: true })} colorValue direction={pnlDirection(data.portfolio_return)} />
            <Stat label="基准收益" value={formatPercent((data.benchmark_return ?? 0) * 100, { sign: true })} colorValue direction={pnlDirection(data.benchmark_return)} />
            <Stat label="Alpha（年化）" value={formatPercent((data.alpha ?? 0) * 100, { sign: true })} colorValue direction={pnlDirection(data.alpha)} />
            <Stat label="Beta" value={data.beta?.toFixed(2) ?? "—"} />
            <Stat label="信息比率" value={data.information_ratio?.toFixed(2) ?? "—"} />
            <Stat label="跟踪误差" value={formatPercent((data.tracking_error ?? 0) * 100)} />
          </div>
          <p className="text-caption text-muted">
            基准：{data.benchmark?.name}（{data.benchmark?.symbol}）· 样本 {data.samples} 个交易日
          </p>
        </>
      )}
    </div>
  );
}
