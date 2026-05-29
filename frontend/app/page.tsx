/**
 * 仪表盘首页（骨架）。
 * Step 1.6 将接入真实 API 与 <Stat> 卡片、净值曲线、Top 持仓等。
 */
export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-h1 text-primary">仪表盘</h1>
        <p className="text-small text-secondary">记录、分析与复盘你的投资决策。</p>
      </div>

      {/* Stat 卡片占位栅格（文档 8.7） */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          { label: "总资产", value: "—" },
          { label: "当日 P&L", value: "—" },
          { label: "年度收益", value: "—" },
          { label: "vs 基准", value: "—" },
        ].map((s) => (
          <div
            key={s.label}
            className="rounded-lg border border-border-subtle bg-surface p-4"
          >
            <div className="text-caption text-secondary">{s.label}</div>
            <div className="tnum mt-2 text-display text-primary">{s.value}</div>
          </div>
        ))}
      </div>

      <div className="rounded-lg border border-border-subtle bg-surface p-6">
        <h2 className="text-h2 text-primary">净值 vs 基准</h2>
        <div className="mt-4 flex h-64 items-center justify-center rounded-md border border-dashed border-border-subtle text-secondary">
          图表占位 — 将在 Phase 3 接入 lightweight-charts
        </div>
      </div>
    </div>
  );
}
