"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { DonutExposure } from "@/components/charts/donut-exposure";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api/client";
import { useT } from "@/lib/i18n/use-t";
import { useUiStore } from "@/lib/store/ui-store";

export default function ExposurePage() {
  const { t } = useT();
  const baseCurrency = useUiStore((s) => s.baseCurrency);
  const [dim, setDim] = useState("industry");
  const DIMENSIONS = [
    { key: "industry", label: t("exposure.industry") },
    { key: "market", label: t("exposure.market") },
    { key: "currency", label: t("exposure.currency") },
  ];
  const { data, isError } = useQuery({
    queryKey: ["exposure", dim, baseCurrency],
    queryFn: async () =>
      (await api.get<any>(`/portfolio/exposure?dimension=${dim}&currency=${baseCurrency}`)).data,
  });
  const { data: conc } = useQuery({
    queryKey: ["concentration", baseCurrency],
    queryFn: async () =>
      (await api.get<any>(`/portfolio/concentration?currency=${baseCurrency}`)).data,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-h1 text-primary">{t("exposure.title")}</h1>
          <p className="text-small text-secondary">{t("exposure.subtitle")}</p>
        </div>
        <div className="flex gap-2">
          {DIMENSIONS.map((d) => (
            <Button key={d.key} size="sm" variant={dim === d.key ? "default" : "outline"} onClick={() => setDim(d.key)}>
              {d.label}
            </Button>
          ))}
        </div>
      </div>

      {conc?.alerts && conc.alerts.length > 0 && (
        <div className="space-y-1 rounded-md border border-warn/40 bg-warn/10 p-3">
          {conc.alerts.map((a: string, i: number) => (
            <p key={i} className="text-small text-warn">{a}</p>
          ))}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>{t("exposure.dimExposure", { dim: DIMENSIONS.find((d) => d.key === dim)?.label ?? "" })}</CardTitle>
        </CardHeader>
        <CardContent>
          {isError ? (
            <p className="py-12 text-center text-meta text-down">{t("exposure.noData")}</p>
          ) : (
            <DonutExposure slices={data?.slices ?? []} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
