"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { Stat } from "@/components/stats/stat";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api/client";
import { formatPercent, pnlDirection } from "@/lib/format";
import { useT } from "@/lib/i18n/use-t";

const MARKETS = ["US", "CN", "HK", "JP"];

export default function BenchmarkPage() {
  const { t } = useT();
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
          <h1 className="text-h1 text-primary">{t("benchmark.title")}</h1>
          <p className="text-small text-secondary">{t("benchmark.subtitle")}</p>
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
        <div className="border-y border-border-default py-8 text-center text-secondary">
          {data?.message ?? t("common.loading")}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 divide-x divide-y divide-border-subtle border-y border-border-default md:grid-cols-4 md:divide-y-0">
            <Stat flat label={t("benchmark.portfolioReturn")} value={formatPercent((data.portfolio_return ?? 0) * 100, { sign: true })} colorValue direction={pnlDirection(data.portfolio_return)} />
            <Stat flat label={t("benchmark.benchmarkReturn")} value={formatPercent((data.benchmark_return ?? 0) * 100, { sign: true })} colorValue direction={pnlDirection(data.benchmark_return)} />
            <Stat flat label={t("benchmark.alpha")} value={formatPercent((data.alpha ?? 0) * 100, { sign: true })} colorValue direction={pnlDirection(data.alpha)} />
            <Stat flat label={t("benchmark.beta")} value={data.beta?.toFixed(2) ?? "—"} />
            <Stat flat label={t("benchmark.infoRatio")} value={data.information_ratio?.toFixed(2) ?? "—"} />
            <Stat flat label={t("benchmark.trackingError")} value={formatPercent((data.tracking_error ?? 0) * 100)} />
          </div>
          <p className="text-caption text-muted">
            {t("benchmark.footnote", {
              name: data.benchmark?.name ?? "",
              symbol: data.benchmark?.symbol ?? "",
              samples: data.samples ?? 0,
            })}
          </p>
        </>
      )}
    </div>
  );
}
