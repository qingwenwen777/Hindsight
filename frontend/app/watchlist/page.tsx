"use client";

import { Plus, Star, Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { PnL } from "@/components/stats/pnl";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { formatMoney } from "@/lib/format";
import { useT } from "@/lib/i18n/use-t";
import { useCreateStock, useStockDiscover, useStockSearch } from "@/lib/hooks/use-portfolio";
import { useAddWatch, useRemoveWatch, useWatchlist } from "@/lib/hooks/use-watchlist";
import type { DiscoverCandidate } from "@/lib/api/types";

export default function WatchlistPage() {
  const { t } = useT();
  const [q, setQ] = useState("");
  const { data: results } = useStockSearch(q);
  const localEmpty = !!q && (results ?? []).length === 0;
  // 本地查不到时，从数据源发现
  const { data: discovered, isFetching: discovering } = useStockDiscover(q, localEmpty);
  const { data: watch } = useWatchlist();
  const add = useAddWatch();
  const remove = useRemoveWatch();
  const createStock = useCreateStock();
  const [adding, setAdding] = useState<string | null>(null);

  const watchedIds = new Set((watch ?? []).map((w) => w.stock_id));

  // 一键：登记（含后台同步行情）→ 加入关注
  const addCandidate = (c: DiscoverCandidate) => {
    const key = `${c.market}:${c.symbol}`;
    setAdding(key);
    createStock.mutate(
      {
        symbol: c.symbol,
        market: c.market,
        name: c.name,
        currency: c.currency,
        is_etf: c.quote_type === "ETF",
        sync: true,
      },
      {
        onSuccess: (stock) => {
          add.mutate(
            { stock_id: stock.id },
            { onSettled: () => setAdding(null) },
          );
          setQ("");
        },
        onError: () => setAdding(null),
      },
    );
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-display text-secondary">{t("watchlist.title")}</h1>
        <p className="mt-2 text-meta text-tertiary">{t("watchlist.subtitle")}</p>
      </div>

      {/* 搜索加入 */}
      <Card>
        <CardContent className="p-5">
          <Input placeholder={t("watchlist.searchPlaceholder")} value={q} onChange={(e) => setQ(e.target.value)} />
          {q && (
            <div className="mt-3 grid gap-1">
              {(results ?? []).map((s) => (
                <div
                  key={s.id}
                  className="flex items-center justify-between rounded-md px-2 py-2 text-body hover:bg-elevated"
                >
                  <Link href={`/stocks/${s.id}`} className="text-primary hover:text-accent">
                    {s.name} <span className="tnum text-tertiary">{s.symbol} · {s.market}</span>
                  </Link>
                  {watchedIds.has(s.id) ? (
                    <span className="text-meta text-tertiary">{t("watchlist.watched")}</span>
                  ) : (
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => add.mutate({ stock_id: s.id })}
                    >
                      <Star className="h-3.5 w-3.5" /> {t("watchlist.watch")}
                    </Button>
                  )}
                </div>
              ))}

              {/* 本地无结果 → 数据源发现 */}
              {localEmpty && (
                <>
                  {(discovered ?? []).length > 0 && (
                    <p className="px-2 pt-1 text-caption text-tertiary">
                      {t("watchlist.discoverHint")}
                    </p>
                  )}
                  {(discovered ?? []).map((c) => {
                    const key = `${c.market}:${c.symbol}`;
                    return (
                      <div
                        key={key}
                        className="flex items-center justify-between rounded-md px-2 py-2 text-body hover:bg-elevated"
                      >
                        <span className="text-primary">
                          {c.name}{" "}
                          <span className="tnum text-tertiary">
                            {c.symbol} · {c.market}
                            {c.exchange ? ` · ${c.exchange}` : ""}
                          </span>
                        </span>
                        <Button
                          size="sm"
                          variant="secondary"
                          disabled={adding === key}
                          onClick={() => addCandidate(c)}
                        >
                          <Plus className="h-3.5 w-3.5" />
                          {adding === key ? t("watchlist.adding") : t("watchlist.addAndSync")}
                        </Button>
                      </div>
                    );
                  })}
                  {(discovered ?? []).length === 0 && (
                    <p className="px-2 py-2 text-meta text-tertiary">
                      {discovering ? t("watchlist.searching") : t("watchlist.notFound")}
                    </p>
                  )}
                </>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 已关注 */}
      <Card className="overflow-hidden">
        <div className="grid grid-cols-[1.4fr_1fr_1fr_auto] items-center gap-4 bg-elevated px-5 py-2.5 label-caps">
          <div>{t("watchlist.col.symbol")}</div>
          <div className="text-right">{t("watchlist.col.lastPrice")}</div>
          <div>{t("watchlist.col.tags")}</div>
          <div className="text-right">{t("watchlist.col.actions")}</div>
        </div>
        {!watch || watch.length === 0 ? (
          <div className="px-5 py-12 text-center text-tertiary">{t("watchlist.empty")}</div>
        ) : (
          watch.map((w) => (
            <div
              key={w.id}
              className="grid grid-cols-[1.4fr_1fr_1fr_auto] items-center gap-4 border-b border-border-default px-5 py-3 last:border-b-0 hover:bg-elevated"
            >
              <Link href={`/stocks/${w.stock_id}`} className="hover:text-accent">
                <div className="font-medium text-primary">{w.name}</div>
                <div className="tnum text-caption text-tertiary">{w.symbol} · {w.market}</div>
              </Link>
              <div className="tnum text-right text-primary">
                {w.last_price ? formatMoney(w.last_price, w.currency) : "—"}
              </div>
              <div className="flex flex-wrap gap-1">
                {(w.tags ?? []).map((t) => (
                  <span key={t} className="rounded-badge border border-border-default bg-base px-1.5 py-0.5 text-caption text-secondary">
                    {t}
                  </span>
                ))}
              </div>
              <div className="text-right">
                <button
                  onClick={() => remove.mutate(w.stock_id)}
                  className="inline-flex h-8 w-8 items-center justify-center rounded-md text-tertiary hover:bg-base hover:text-danger"
                  aria-label={t("watchlist.unwatch")}
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))
        )}
      </Card>
    </div>
  );
}
