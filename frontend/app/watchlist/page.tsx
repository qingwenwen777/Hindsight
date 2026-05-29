"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api/client";
import { useStockSearch } from "@/lib/hooks/use-portfolio";

export default function WatchlistPage() {
  const [q, setQ] = useState("");
  const { data: results } = useStockSearch(q);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-h1 text-primary">关注列表</h1>
        <p className="text-small text-secondary">搜索并跳转个股详情。</p>
      </div>

      <Card>
        <CardContent className="p-4">
          <Input placeholder="搜索代码或名称…" value={q} onChange={(e) => setQ(e.target.value)} />
          <div className="mt-3 space-y-1">
            {(results ?? []).map((s) => (
              <Link
                key={s.id}
                href={`/stocks/${s.id}`}
                className="flex items-center justify-between rounded-md px-2 py-2 text-small hover:bg-elevated"
              >
                <span className="text-primary">{s.name}</span>
                <span className="tnum text-secondary">{s.symbol} · {s.market}</span>
              </Link>
            ))}
            {q && (results ?? []).length === 0 && (
              <p className="px-2 py-2 text-small text-secondary">未找到匹配股票。</p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
