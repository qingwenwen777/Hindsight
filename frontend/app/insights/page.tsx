"use client";

import { Download, FileText, Settings } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { useT } from "@/lib/i18n/use-t";
import {
  downloadInsightDoc,
  useGenerateDaily,
  useInsightDocuments,
} from "@/lib/hooks/use-insights";
import { cn } from "@/lib/utils";

const MARKETS = ["US", "CN", "HK", "JP"];

export default function InsightsPage() {
  const { t } = useT();
  const [type, setType] = useState<string>("");
  const [page, setPage] = useState(1);
  const pageSize = 20;
  const { data, isLoading } = useInsightDocuments(type || undefined, undefined, page, pageSize);
  const generate = useGenerateDaily();
  const [genMarket, setGenMarket] = useState("US");

  const docs = data?.data ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-display text-secondary">{t("insights.title")}</h1>
          <p className="mt-2 text-meta text-tertiary">{t("insights.subtitle")}</p>
        </div>
        <div className="flex items-center gap-2">
          <Select
            value={genMarket}
            onValueChange={setGenMarket}
            options={MARKETS.map((m) => ({ value: m, label: m }))}
            className="h-[34px] w-24"
          />
          <Button
            variant="secondary"
            disabled={generate.isPending}
            onClick={() => generate.mutate(genMarket)}
          >
            {generate.isPending ? t("insights.generating") : t("insights.generate")}
          </Button>
          <Link href="/insights/config">
            <Button variant="outline">
              <Settings className="h-3.5 w-3.5" /> {t("insights.config")}
            </Button>
          </Link>
        </div>
      </div>

      {/* 类型过滤 */}
      <div className="flex gap-2">
        {[
          { v: "", label: t("insights.all") },
          { v: "DAILY_REPORT", label: t("insights.typeDaily") },
          { v: "SCREENER_REVIEW", label: t("insights.typeScreener") },
        ].map((tab) => (
          <Button
            key={tab.v}
            size="sm"
            variant={type === tab.v ? "default" : "outline"}
            onClick={() => {
              setType(tab.v);
              setPage(1);
            }}
          >
            {tab.label}
          </Button>
        ))}
      </div>

      <Card className="overflow-hidden">
        {isLoading ? (
          [0, 1, 2].map((i) => (
            <div key={i} className="border-b border-border-default px-5 py-3">
              <div className="h-6 animate-pulse rounded bg-elevated" />
            </div>
          ))
        ) : docs.length === 0 ? (
          <div className="px-5 py-12 text-center">
            <FileText className="mx-auto mb-3 h-8 w-8 text-tertiary" />
            <div className="text-body text-secondary">{t("insights.empty")}</div>
            <div className="mt-1 text-meta text-tertiary">{t("insights.emptyHint")}</div>
          </div>
        ) : (
          docs.map((d) => (
            <div
              key={d.id}
              className="flex items-center justify-between gap-3 border-b border-border-default px-5 py-3 last:border-b-0 hover:bg-elevated"
            >
              <Link href={`/insights/${d.id}`} className="flex min-w-0 flex-1 items-center gap-3">
                {!d.is_read && <span className="h-2 w-2 shrink-0 rounded-full bg-accent" />}
                <div className="min-w-0">
                  <div className="truncate text-body text-primary">{d.title}</div>
                  <div className="mt-0.5 flex items-center gap-2 text-caption text-tertiary">
                    <span className="rounded-badge border border-border-default px-1.5">
                      {d.doc_type === "DAILY_REPORT" ? t("insights.typeDaily") : t("insights.typeScreener")}
                    </span>
                    {d.market && <span>{d.market}</span>}
                    {d.degraded && <span className="text-warn">{t("insights.degraded")}</span>}
                    <span className="tnum">{(d.created_at ?? "").slice(0, 16).replace("T", " ")}</span>
                  </div>
                </div>
              </Link>
              <button
                onClick={() => downloadInsightDoc(d.id)}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-tertiary hover:bg-base hover:text-primary"
                aria-label={t("insights.download")}
                title={t("insights.download")}
              >
                <Download className="h-4 w-4" />
              </button>
            </div>
          ))
        )}
      </Card>

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3">
          <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            {t("insights.prev")}
          </Button>
          <span className="text-meta text-tertiary">{t("insights.page", { page })}</span>
          <Button size="sm" variant="outline" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
            {t("insights.next")}
          </Button>
        </div>
      )}
    </div>
  );
}
