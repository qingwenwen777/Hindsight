"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";

import { LockBadge } from "@/components/forms/lock-badge";
import { EMOTIONS } from "@/components/forms/emotion-picker";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api/client";
import { formatDate, formatMoney } from "@/lib/format";
import { useT, type TFunc } from "@/lib/i18n/use-t";
import { useJournal } from "@/lib/hooks/use-portfolio";
import type { Review } from "@/lib/api/types";

function emotionLabel(t: TFunc, value?: string | null) {
  const e = EMOTIONS.find((x) => x.value === value);
  return e ? `${e.emoji} ${t(`form.emotion.${e.value}`)}` : value || "—";
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <div className="text-caption text-secondary">{label}</div>
      <div className="tnum text-small text-primary">{value ?? "—"}</div>
    </div>
  );
}

export default function JournalDetailPage() {
  const { t } = useT();
  const params = useParams();
  const id = Number(params.id);
  const { data: journal, isLoading } = useJournal(id);
  const { data: reviews } = useQuery({
    queryKey: ["reviews", id],
    queryFn: async () => (await api.get<Review[]>(`/journals/${id}/reviews`)).data,
    enabled: Number.isFinite(id),
  });

  if (isLoading) {
    return <div className="h-64 animate-pulse rounded-lg bg-elevated" />;
  }
  if (!journal) {
    return <Card className="p-12 text-center text-secondary">{t("journal.notFound")}</Card>;
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-h1 text-primary">{t("journal.detailTitle", { id: journal.id })}</h1>
          <p className="text-small text-secondary">{t("journal.detailSubtitle")}</p>
        </div>
        {journal.is_locked && <LockBadge lockedAt={journal.locked_at} />}
      </div>

      {/* 决策快照（灰底强调只读） */}
      <Card className="bg-base">
        <CardHeader>
          <CardTitle>{t("journal.snapshot")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
            <Field label={t("journal.decisionType")} value={journal.decision_type} />
            <Field label={t("journal.thesisCategory")} value={journal.thesis_category} />
            <Field label={t("journal.expectedHorizon")} value={journal.expected_horizon} />
            <Field label={t("journal.targetPrice")} value={formatMoney(journal.target_price)} />
            <Field label={t("journal.stopLoss")} value={formatMoney(journal.stop_loss_price)} />
            <Field label={t("journal.confidence")} value={journal.confidence ? `${journal.confidence}/5` : "—"} />
            <Field label={t("journal.emotion")} value={emotionLabel(t, journal.emotion)} />
          </div>
          <div className="space-y-1">
            <div className="text-caption text-secondary">{t("journal.thesis")}</div>
            <p className="whitespace-pre-wrap text-small text-primary">{journal.thesis}</p>
          </div>
          {journal.risks && (
            <div className="space-y-1">
              <div className="text-caption text-secondary">{t("journal.risks")}</div>
              <p className="whitespace-pre-wrap text-small text-primary">{journal.risks}</p>
            </div>
          )}
          {journal.exit_condition && (
            <Field label={t("journal.exitCondition")} value={journal.exit_condition} />
          )}
        </CardContent>
      </Card>

      {/* 复盘时间线 */}
      <Card>
        <CardHeader>
          <CardTitle>{t("journal.reviewTimeline")}</CardTitle>
        </CardHeader>
        <CardContent>
          {!reviews || reviews.length === 0 ? (
            <p className="py-6 text-center text-small text-secondary">
              {t("journal.noReviews")}
            </p>
          ) : (
            <div className="space-y-3">
              {reviews.map((r) => (
                <div key={r.id} className="rounded-md border border-border-subtle p-3">
                  <div className="flex items-center justify-between">
                    <span className="tnum text-small text-primary">{formatDate(r.review_date)}</span>
                    {r.days_since_decision != null && (
                      <span className="text-caption text-secondary">
                        +{r.days_since_decision} {t("journal.daysSuffix")}
                      </span>
                    )}
                  </div>
                  {r.lessons && <p className="mt-2 text-small text-primary">{r.lessons}</p>}
                  {r.luck_vs_skill && (
                    <span className="mt-1 inline-block text-caption text-muted">
                      {t("journal.attribution")}{r.luck_vs_skill}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
