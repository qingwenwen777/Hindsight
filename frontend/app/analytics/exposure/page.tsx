"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { DonutExposure } from "@/components/charts/donut-exposure";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api/client";

const DIMENSIONS = [
  { key: "industry", label: "行业" },
  { key: "market", label: "市场" },
  { key: "currency", label: "币种" },
];

export default function ExposurePage() {
  const [dim, setDim] = useState("industry");
  const { data } = useQuery({
    queryKey: ["exposure", dim],
    queryFn: async () => (await api.get<any>(`/portfolio/exposure?dimension=${dim}`)).data,
  });
  const { data: conc } = useQuery({
    queryKey: ["concentration"],
    queryFn: async () => (await api.get<any>("/portfolio/concentration")).data,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-h1 text-primary">暴露分析</h1>
          <p className="text-small text-secondary">行业/市场/币种维度暴露与集中度。</p>
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
          <CardTitle>{DIMENSIONS.find((d) => d.key === dim)?.label}暴露</CardTitle>
        </CardHeader>
        <CardContent>
          <DonutExposure slices={data?.slices ?? []} />
        </CardContent>
      </Card>
    </div>
  );
}
