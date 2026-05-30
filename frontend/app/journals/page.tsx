"use client";

import Link from "next/link";

import { LockBadge } from "@/components/forms/lock-badge";
import { Card } from "@/components/ui/card";
import { EMOTIONS } from "@/components/forms/emotion-picker";
import { formatDate } from "@/lib/format";
import { useT, type TFunc } from "@/lib/i18n/use-t";
import { useJournals } from "@/lib/hooks/use-portfolio";

function emotionLabel(t: TFunc, value?: string | null) {
  const e = EMOTIONS.find((x) => x.value === value);
  return e ? `${e.emoji} ${t(`form.emotion.${e.value}`)}` : value || "—";
}

export default function JournalsPage() {
  const { t } = useT();
  const { data: journals, isLoading } = useJournals();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-h1 text-primary">{t("journals.title")}</h1>
        <p className="text-small text-secondary">{t("journals.subtitle")}</p>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-20 animate-pulse rounded-lg bg-elevated" />
          ))}
        </div>
      ) : !journals || journals.length === 0 ? (
        <Card className="p-12 text-center text-secondary">{t("journals.empty")}</Card>
      ) : (
        <div className="space-y-3">
          {journals.map((j) => (
            <Link key={j.id} href={`/journals/${j.id}`}>
              <Card className="p-4 transition-colors hover:bg-elevated">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="rounded-sm bg-accent/10 px-2 py-0.5 text-caption text-accent">
                        {j.decision_type}
                      </span>
                      {j.thesis_category && (
                        <span className="text-caption text-secondary">{j.thesis_category}</span>
                      )}
                      <span className="text-caption text-muted">{emotionLabel(t, j.emotion)}</span>
                    </div>
                    <p className="line-clamp-2 text-small text-primary">{j.thesis}</p>
                    <p className="text-caption text-muted">{formatDate(j.created_at)}</p>
                  </div>
                  {j.is_locked && <LockBadge lockedAt={j.locked_at} />}
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
