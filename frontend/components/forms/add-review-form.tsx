"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useAddReview, type ReviewCreate } from "@/lib/hooks/use-reviews";
import { useT } from "@/lib/i18n/use-t";
import { cn } from "@/lib/utils";

const ATTRIBUTIONS = ["SKILL", "LUCK", "MIXED"] as const;

/** 追加复盘表单：日期 + 盈亏% + 逻辑是否成立 + 归因 + 心得。 */
export function AddReviewForm({ journalId, onDone }: { journalId: number; onDone?: () => void }) {
  const { t } = useT();
  const addReview = useAddReview(journalId);

  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [pnlPct, setPnlPct] = useState("");
  const [thesisHeld, setThesisHeld] = useState<boolean | null>(null);
  const [attribution, setAttribution] = useState<string | null>(null);
  const [lessons, setLessons] = useState("");

  const submit = () => {
    const payload: ReviewCreate = {
      review_date: date,
      pnl_pct: pnlPct.trim() ? pnlPct.trim() : undefined,
      thesis_held: thesisHeld,
      luck_vs_skill: attribution,
      lessons: lessons.trim() ? lessons.trim() : undefined,
    };
    addReview.mutate(payload, {
      onSuccess: () => {
        setPnlPct("");
        setThesisHeld(null);
        setAttribution(null);
        setLessons("");
        onDone?.();
      },
    });
  };

  return (
    <div className="space-y-4 rounded-md border border-border-subtle bg-base p-4">
      <div className="text-body font-medium text-primary">{t("review.formTitle")}</div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <label className="space-y-1.5">
          <span className="text-caption text-secondary">{t("review.date")}</span>
          <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="tnum" />
        </label>
        <label className="space-y-1.5">
          <span className="text-caption text-secondary">{t("review.pnlPct")}</span>
          <Input
            type="number"
            inputMode="decimal"
            placeholder="0.0"
            value={pnlPct}
            onChange={(e) => setPnlPct(e.target.value)}
            className="tnum"
          />
        </label>
      </div>

      {/* 逻辑是否成立 */}
      <div className="space-y-1.5">
        <span className="text-caption text-secondary">{t("review.thesisHeld")}</span>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setThesisHeld(thesisHeld === true ? null : true)}
            className={cn(
              "rounded-md border px-3 py-1.5 text-meta transition-colors",
              thesisHeld === true
                ? "border-up/50 bg-up/10 text-up"
                : "border-border-subtle text-secondary hover:bg-elevated",
            )}
          >
            {t("review.held")}
          </button>
          <button
            type="button"
            onClick={() => setThesisHeld(thesisHeld === false ? null : false)}
            className={cn(
              "rounded-md border px-3 py-1.5 text-meta transition-colors",
              thesisHeld === false
                ? "border-down/50 bg-down/10 text-down"
                : "border-border-subtle text-secondary hover:bg-elevated",
            )}
          >
            {t("review.broken")}
          </button>
        </div>
      </div>

      {/* 归因 */}
      <div className="space-y-1.5">
        <span className="text-caption text-secondary">{t("review.attribution")}</span>
        <div className="flex gap-2">
          {ATTRIBUTIONS.map((a) => (
            <button
              key={a}
              type="button"
              onClick={() => setAttribution(attribution === a ? null : a)}
              className={cn(
                "rounded-md border px-3 py-1.5 text-meta transition-colors",
                attribution === a
                  ? "border-accent bg-accent/10 text-primary"
                  : "border-border-subtle text-secondary hover:bg-elevated",
              )}
            >
              {t(`review.luckVsSkill.${a}`)}
            </button>
          ))}
        </div>
      </div>

      {/* 心得 */}
      <label className="block space-y-1.5">
        <span className="text-caption text-secondary">{t("review.lessons")}</span>
        <Textarea
          value={lessons}
          onChange={(e) => setLessons(e.target.value)}
          placeholder={t("review.lessonsPlaceholder")}
          rows={3}
        />
      </label>

      {addReview.isError && <p className="text-meta text-down">{t("review.failed")}</p>}

      <div className="flex justify-end gap-2">
        {onDone && (
          <Button variant="ghost" size="sm" onClick={onDone} disabled={addReview.isPending}>
            {t("review.cancel")}
          </Button>
        )}
        <Button size="sm" onClick={submit} disabled={addReview.isPending}>
          {addReview.isPending ? t("review.submitting") : t("review.submit")}
        </Button>
      </div>
    </div>
  );
}
