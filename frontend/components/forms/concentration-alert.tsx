import { AlertTriangle } from "lucide-react";

interface ConcentrationAlertProps {
  warnings: string[];
}

/**
 * 集中度/防御告警条（设计文档 8.5 <ConcentrationAlert>）。
 * 超阈值或防御规则命中时出现，警告色。
 */
export function ConcentrationAlert({ warnings }: ConcentrationAlertProps) {
  if (!warnings || warnings.length === 0) return null;
  return (
    <div className="space-y-1 rounded-md border border-warn/40 bg-warn/10 p-3">
      {warnings.map((w, i) => (
        <div key={i} className="flex items-start gap-2 text-small text-warn">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{w}</span>
        </div>
      ))}
    </div>
  );
}
