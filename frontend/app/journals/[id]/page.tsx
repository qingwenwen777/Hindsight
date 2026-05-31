"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import { Lock, Plus } from "lucide-react";

import { AddReviewForm } from "@/components/forms/add-review-form";
import { EMOTIONS } from "@/components/forms/emotion-picker";
import { Button } from "@/components/ui/button";
import { formatDate, formatMoney, formatPercent, pnlDirection } from "@/lib/format";
import { useT, type TFunc } from "@/lib/i18n/use-t";
import { useJournal } from "@/lib/hooks/use-portfolio";
import { useReviews } from "@/lib/hooks/use-reviews";
import { cn } from "@/lib/utils";

function emotionLabel(t: TFunc, value?: string | null) {
  const e = EMOTIONS.find((x) => x.value === value);
  return e ? `${e.emoji} ${t(`form.emotion.${e.value}`)}` : value || "—";
}

/** 只读字段：label 上、value 下，等宽对齐。 */
function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <div className="text-caption text-tertiary">{label}</div>
      <div className="tnum text-body text-primary">{value ?? "—"}</div>
    </div>
  );
}

export default function JournalDetailPage() {
  const { t } = useT();
  const params = useParams();
  const id = Number(params.id);
  const { data: journal, isLoading } = useJournal(id);
  const { data: reviews } = useReviews(id);
  const [showForm, setShowForm] = useState(false);

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl space-y-4">
        <div className="space-y-2">
          <div className="skeleton h-7 w-48" />
          <div className="skeleton h-3.5 w-72" />
        </div>
        <div className="skeleton h-64 rounded-card" />
      </div>
    );
  }
  if (!journal) {
    return <div className="border-y border-border-default py-12 text-center text-tertiary">{t("journal.notFound")}</div>;
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      {/* 页头 */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-display text-secondary">{t("journal.detailTitle", { id: journal.id })}</h1>
          <p className="mt-2 text-meta text-tertiary">{t("journal.detailSubtitle")}</p>
        </div>
        {journal.is_locked && (
          <span className="inline-flex shrink-0 items-center gap-1.5 rounded-badge border border-border-default bg-elevated px-2 py-1 text-badge font-medium text-secondary">
            <Lock className="h-3 w-3" />
            {t("form.locked")}
            {journal.locked_at ? ` · ${formatDate(journal.locked_at)}` : ""}
          </span>
        )}
      </div>

      {/* 决策快照 */}
      <section>
        <h2 className="border-b border-border-default pb-2 text-title font-medium text-primary">
          {t("journal.snapshot")}
        </h2>
        <div className="space-y-5 pt-4">
          <div className="grid grid-cols-2 gap-x-4 gap-y-4 sm:grid-cols-3">
            <Field label={t("journal.decisionType")} value={journal.decision_type} />
            <Field label={t("journal.thesisCategory")} value={journal.thesis_category} />
            <Field label={t("journal.expectedHorizon")} value={journal.expected_horizon} />
            <Field
              label={t("journal.targetPrice")}
              value={journal.target_price ? formatMoney(journal.target_price) : "—"}
            />
            <Field
              label={t("journal.stopLoss")}
              value={journal.stop_loss_price ? formatMoney(journal.stop_loss_price) : "—"}
            />
            <Field
              label={t("journal.confidence")}
              value={journal.confidence ? `${journal.confidence}/5` : "—"}
            />
            <Field label={t("journal.emotion")} value={emotionLabel(t, journal.emotion)} />
          </div>

          <div className="space-y-1.5 border-t border-border-subtle pt-4">
            <div className="text-caption text-tertiary">{t("journal.thesis")}</div>
            <p className="whitespace-pre-wrap text-body leading-relaxed text-primary">
              {journal.thesis}
            </p>
          </div>
          {journal.risks && (
            <div className="space-y-1.5">
              <div className="text-caption text-tertiary">{t("journal.risks")}</div>
              <p className="whitespace-pre-wrap text-body leading-relaxed text-primary">
                {journal.risks}
              </p>
            </div>
          )}
          {journal.exit_condition && (
            <div className="space-y-1.5">
              <div className="text-caption text-tertiary">{t("journal.exitCondition")}</div>
              <p className="whitespace-pre-wrap text-body text-primary">{journal.exit_condition}</p>
            </div>
          )}
        </div>
      </section>

      {/* 复盘时间线 */}
      <section>
        <div className="flex flex-row items-center justify-between border-b border-border-default pb-2">
          <h2 className="text-title font-medium text-primary">{t("journal.reviewTimeline")}</h2>
          {!showForm && (
            <Button size="sm" variant="secondary" onClick={() => setShowForm(true)}>
              <Plus className="h-3.5 w-3.5" />
              {t("review.add")}
            </Button>
          )}
        </div>
        <div className="space-y-4 pt-4">
          {showForm && <AddReviewForm journalId={id} onDone={() => setShowForm(false)} />}

          {!reviews || reviews.length === 0 ? (
            !showForm && (
              <p className="py-6 text-center text-meta text-tertiary">{t("journal.noReviews")}</p>
            )
          ) : (
            <ol className="relative space-y-4 border-l border-border-subtle pl-5">
              {reviews.map((r) => {
                const pnl = r.pnl_pct != null ? Number(r.pnl_pct) : null;
                const dir = pnlDirection(pnl);
                return (
                  <li key={r.id} className="relative">
                    {/* 时间线圆点 */}
                    <span className="absolute -left-[23px] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-base bg-border-strong" />
                    <div className="rounded-md border border-border-subtle bg-surface p-3.5">
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                        <span className="tnum text-body font-medium text-primary">
                          {formatDate(r.review_date)}
                        </span>
                        {r.days_since_decision != null && (
                          <span className="text-caption text-tertiary">
                            +{r.days_since_decision} {t("journal.daysSuffix")}
                          </span>
                        )}
                        {pnl != null && (
                          <span
                            className={cn(
                              "tnum text-meta font-medium",
                              dir === "up" ? "text-up" : dir === "down" ? "text-down" : "text-secondary",
                            )}
                          >
                            {t("review.pnlLabel")} {formatPercent(pnl, { sign: true })}
                          </span>
                        )}
                        {r.thesis_held != null && (
                          <span
                            className={cn(
                              "rounded-badge border px-1.5 py-0.5 text-badge font-medium",
                              r.thesis_held
                                ? "border-up/45 text-up"
                                : "border-down/45 text-down",
                            )}
                          >
                            {r.thesis_held ? t("review.thesisHeldYes") : t("review.thesisHeldNo")}
                          </span>
                        )}
                        {r.luck_vs_skill && (
                          <span className="rounded-badge border border-border-default px-1.5 py-0.5 text-badge text-secondary">
                            {t(`review.luckVsSkill.${r.luck_vs_skill}`)}
                          </span>
                        )}
                      </div>
                      {r.lessons && (
                        <p className="mt-2 whitespace-pre-wrap text-body leading-relaxed text-primary">
                          {r.lessons}
                        </p>
                      )}
                      {r.notes && <p className="mt-1.5 text-meta text-tertiary">{r.notes}</p>}
                    </div>
                  </li>
                );
              })}
            </ol>
          )}
        </div>
      </section>
    </div>
  );
}
