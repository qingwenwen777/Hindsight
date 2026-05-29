"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";

import { LockBadge } from "@/components/forms/lock-badge";
import { EMOTIONS } from "@/components/forms/emotion-picker";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api/client";
import { formatDate, formatMoney } from "@/lib/format";
import { useJournal } from "@/lib/hooks/use-portfolio";
import type { Review } from "@/lib/api/types";

function emotionLabel(value?: string | null) {
  const e = EMOTIONS.find((x) => x.value === value);
  return e ? `${e.emoji} ${e.label}` : value || "—";
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
    return <Card className="p-12 text-center text-secondary">日志不存在。</Card>;
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-h1 text-primary">决策日志 #{journal.id}</h1>
          <p className="text-small text-secondary">这是你当时写的，不可修改，只能追加复盘。</p>
        </div>
        {journal.is_locked && <LockBadge lockedAt={journal.locked_at} />}
      </div>

      {/* 决策快照（灰底强调只读） */}
      <Card className="bg-base">
        <CardHeader>
          <CardTitle>决策快照</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
            <Field label="决策类型" value={journal.decision_type} />
            <Field label="论点类别" value={journal.thesis_category} />
            <Field label="预期持有" value={journal.expected_horizon} />
            <Field label="目标价" value={formatMoney(journal.target_price)} />
            <Field label="止损价" value={formatMoney(journal.stop_loss_price)} />
            <Field label="信心" value={journal.confidence ? `${journal.confidence}/5` : "—"} />
            <Field label="情绪" value={emotionLabel(journal.emotion)} />
          </div>
          <div className="space-y-1">
            <div className="text-caption text-secondary">投资逻辑</div>
            <p className="whitespace-pre-wrap text-small text-primary">{journal.thesis}</p>
          </div>
          {journal.risks && (
            <div className="space-y-1">
              <div className="text-caption text-secondary">主要风险</div>
              <p className="whitespace-pre-wrap text-small text-primary">{journal.risks}</p>
            </div>
          )}
          {journal.exit_condition && (
            <Field label="退出条件" value={journal.exit_condition} />
          )}
        </CardContent>
      </Card>

      {/* 复盘时间线 */}
      <Card>
        <CardHeader>
          <CardTitle>复盘时间线</CardTitle>
        </CardHeader>
        <CardContent>
          {!reviews || reviews.length === 0 ? (
            <p className="py-6 text-center text-small text-secondary">
              还没有复盘记录。到期提醒将引导你回顾。
            </p>
          ) : (
            <div className="space-y-3">
              {reviews.map((r) => (
                <div key={r.id} className="rounded-md border border-border-subtle p-3">
                  <div className="flex items-center justify-between">
                    <span className="tnum text-small text-primary">{formatDate(r.review_date)}</span>
                    {r.days_since_decision != null && (
                      <span className="text-caption text-secondary">
                        +{r.days_since_decision} 天
                      </span>
                    )}
                  </div>
                  {r.lessons && <p className="mt-2 text-small text-primary">{r.lessons}</p>}
                  {r.luck_vs_skill && (
                    <span className="mt-1 inline-block text-caption text-muted">
                      归因：{r.luck_vs_skill}
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
