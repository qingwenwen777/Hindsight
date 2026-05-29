"use client";

import { useQuery } from "@tanstack/react-query";

import { Stat } from "@/components/stats/stat";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api/client";
import { formatMoney, formatPercent, pnlDirection } from "@/lib/format";

export default function ReturnsPage() {
  const { data: irr } = useQuery({
    queryKey: ["returns", "IRR"],
    queryFn: async () => (await api.get<any>("/portfolio/returns?type=IRR")).data,
  });
  const { data: twr } = useQuery({
    queryKey: ["returns", "TWR"],
    queryFn: async () => (await api.get<any>("/portfolio/returns?type=TWR")).data,
  });

  const irrPct = irr?.annualized_pct ? Number(irr.annualized_pct) : null;
  const twrPct = twr?.twr_pct ? Number(twr.twr_pct) : null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-h1 text-primary">收益分析</h1>
        <p className="text-small text-secondary">时间加权（TWR）与内部收益率（IRR）。</p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Stat
          label="IRR（年化）"
          value={irrPct != null ? formatPercent(irrPct, { sign: true }) : "—"}
          colorValue
          direction={pnlDirection(irrPct)}
        />
        <Stat
          label="TWR"
          value={twrPct != null ? formatPercent(twrPct, { sign: true }) : "—"}
          colorValue
          direction={pnlDirection(twrPct)}
        />
        <Stat
          label="当前市值"
          value={irr?.current_value ? formatMoney(irr.current_value) : "—"}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>说明</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-small text-secondary">
          <p>IRR 基于入金/出金现金流 + 当前市值用 brentq 求解年化内部收益率。</p>
          <p>TWR 在缺逐日估值快照时为简化口径（单段），逐日估值快照接入后将精确分段。</p>
          {twr?.note && <p className="text-muted">TWR 备注：{twr.note}</p>}
        </CardContent>
      </Card>
    </div>
  );
}
