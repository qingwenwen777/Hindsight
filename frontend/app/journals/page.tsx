"use client";

import Link from "next/link";
import { ChevronRight, Lock } from "lucide-react";

import { FadeIn, staggerDelay } from "@/components/ui/fade-in";
import { RefetchIndicator } from "@/components/ui/refetch-indicator";
import { Skeleton } from "@/components/ui/skeleton";
import { EMOTIONS } from "@/components/forms/emotion-picker";
import { formatDate } from "@/lib/format";
import { useT, type TFunc } from "@/lib/i18n/use-t";
import { useJournals } from "@/lib/hooks/use-portfolio";

function emotionLabel(t: TFunc, value?: string | null) {
  const e = EMOTIONS.find((x) => x.value === value);
  return e ? `${e.emoji} ${t(`form.emotion.${e.value}`)}` : null;
}

/** 决策类型 -> 语义色（左侧竖条 + 文字）。 */
function decisionTone(type: string): { bar: string; text: string } {
  const t = type.toUpperCase();
  if (t === "BUY") return { bar: "bg-up", text: "text-up" };
  if (t === "SELL") return { bar: "bg-down", text: "text-down" };
  if (t === "HOLD") return { bar: "bg-accent", text: "text-accent" };
  return { bar: "bg-border-strong", text: "text-secondary" };
}

export default function JournalsPage() {
  const { t } = useT();
  const { data: journals, isLoading, isFetching } = useJournals();

  return (
    <div className="space-y-4">
      <RefetchIndicator active={isFetching && !isLoading} />
      <div>
        <h1 className="text-display text-secondary">{t("journals.title")}</h1>
        <p className="mt-2 text-meta text-tertiary">{t("journals.subtitle")}</p>
      </div>

      {isLoading ? (
        <div className="divide-y divide-border-subtle border-y border-border-default">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="flex items-center gap-3 px-1 py-3.5">
              <Skeleton className="h-9 w-0.5 rounded-full" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-3.5 w-40" />
                <Skeleton className="h-3.5 w-3/4" />
              </div>
            </div>
          ))}
        </div>
      ) : !journals || journals.length === 0 ? (
        <div className="border-y border-border-default py-12 text-center text-tertiary">{t("journals.empty")}</div>
      ) : (
        <div className="divide-y divide-border-subtle border-y border-border-default">
          {journals.map((j, i) => {
            const tone = decisionTone(j.decision_type);
            const emo = emotionLabel(t, j.emotion);
            return (
              <FadeIn
                as={Link}
                key={j.id}
                delay={staggerDelay(i)}
                href={`/journals/${j.id}`}
                className="group flex items-stretch gap-3 px-1 py-3.5 transition-colors duration-150 hover:bg-elevated/50"
              >
                {/* 左侧语义色竖条 */}
                <span className={`w-0.5 shrink-0 rounded-full ${tone.bar}`} />

                <div className="min-w-0 flex-1 space-y-1.5">
                  {/* 第一行：决策类型 + 类别 + 日期（单行，简洁） */}
                  <div className="flex items-center gap-2 text-meta">
                    <span className={`font-semibold ${tone.text}`}>{j.decision_type}</span>
                    {j.thesis_category && (
                      <>
                        <span className="text-border-strong">·</span>
                        <span className="text-secondary">{j.thesis_category}</span>
                      </>
                    )}
                    {emo && (
                      <>
                        <span className="text-border-strong">·</span>
                        <span className="text-tertiary">{emo}</span>
                      </>
                    )}
                    <span className="ml-auto tnum text-tertiary">{formatDate(j.created_at)}</span>
                  </div>

                  {/* 第二行：投资逻辑摘要 */}
                  <p className="line-clamp-1 text-body text-primary">{j.thesis}</p>
                </div>

                {/* 右侧：锁定图标 + 进入箭头（轻量，不再用大胶囊） */}
                <div className="flex shrink-0 items-center gap-2 self-center text-tertiary">
                  {j.is_locked && <Lock className="h-3.5 w-3.5" />}
                  <ChevronRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                </div>
              </FadeIn>
            );
          })}
        </div>
      )}
    </div>
  );
}
