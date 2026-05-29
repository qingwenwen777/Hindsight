import { Lock } from "lucide-react";

import { formatDate } from "@/lib/format";

interface LockBadgeProps {
  lockedAt?: string | null;
}

/**
 * 日志锁定标识（设计文档 8.5 <LockBadge>）。
 * 明示不可改。
 */
export function LockBadge({ lockedAt }: LockBadgeProps) {
  return (
    <span className="inline-flex items-center gap-1 rounded-sm bg-elevated px-2 py-1 text-caption text-secondary">
      <Lock className="h-3 w-3" />
      已锁定{lockedAt ? ` · ${formatDate(lockedAt)}` : ""}
    </span>
  );
}
