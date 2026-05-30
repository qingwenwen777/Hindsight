"use client";

import { ArrowLeft, Download } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect } from "react";

import { Markdown } from "@/components/insights/markdown";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useT } from "@/lib/i18n/use-t";
import {
  downloadInsightDoc,
  useInsightDoc,
  useMarkInsightRead,
} from "@/lib/hooks/use-insights";

export default function InsightDetailPage() {
  const { t } = useT();
  const params = useParams();
  const id = Number(params.id);
  const { data: doc, isLoading } = useInsightDoc(id);
  const markRead = useMarkInsightRead();

  // 打开即标记已读
  useEffect(() => {
    if (doc && !doc.is_read) markRead.mutate(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doc?.id]);

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div className="flex items-center justify-between">
        <Link href="/insights" className="inline-flex items-center gap-1.5 text-meta text-tertiary hover:text-primary">
          <ArrowLeft className="h-4 w-4" /> {t("insights.back")}
        </Link>
        {doc && (
          <Button variant="outline" size="sm" onClick={() => downloadInsightDoc(id)}>
            <Download className="h-3.5 w-3.5" /> {t("insights.download")}
          </Button>
        )}
      </div>

      {isLoading ? (
        <div className="h-64 animate-pulse rounded-lg bg-elevated" />
      ) : !doc ? (
        <Card className="p-12 text-center text-secondary">{t("insights.notFound")}</Card>
      ) : (
        <Card className="p-6">
          {doc.degraded && doc.degraded_reason && (
            <div className="mb-4 rounded-md border border-warn/40 bg-warn/10 px-3 py-2 text-meta text-warn">
              {t("insights.degradedNote")} {doc.degraded_reason}
            </div>
          )}
          <Markdown content={doc.body_md} />
          {doc.model && (
            <div className="mt-6 border-t border-border-default pt-3 text-caption text-muted">
              {doc.model}
              {doc.prompt_tokens != null && (
                <span className="tnum">
                  {" "}· {(doc.prompt_tokens ?? 0) + (doc.completion_tokens ?? 0)} tokens
                </span>
              )}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
