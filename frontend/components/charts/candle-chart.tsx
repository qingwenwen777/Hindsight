"use client";

import {
  ColorType,
  type IChartApi,
  type ISeriesApi,
  type SeriesMarker,
  type Time,
  createChart,
} from "lightweight-charts";
import { useEffect, useRef } from "react";

import type { PriceBar, IndicatorData } from "@/lib/hooks/use-stock";
import type { Transaction } from "@/lib/api/types";
import { useUiStore } from "@/lib/store/ui-store";

interface CandleChartProps {
  prices: PriceBar[];
  indicators?: IndicatorData;
  transactions?: Transaction[];
  height?: number;
  showBoll?: boolean;
  showMa?: boolean;
}

/** 读取 CSS 变量当前值 */
function cssVar(name: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

/**
 * K 线主图（设计文档 8.6）—— lightweight-charts。
 * 蜡烛 + 成交量 + 可选 MA/布林带叠加 + 自有交易买卖点 marker。
 * 涨跌色随 colorScheme（asia/western）切换。
 */
export function CandleChart({
  prices,
  indicators,
  transactions = [],
  height = 480,
  showBoll = true,
  showMa = true,
}: CandleChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const colorScheme = useUiStore((s) => s.colorScheme);

  useEffect(() => {
    if (!containerRef.current || prices.length === 0) return;

    const upColor = colorScheme === "asia" ? cssVar("--color-red", "#ef5350") : cssVar("--color-green", "#26a69a");
    const downColor = colorScheme === "asia" ? cssVar("--color-green", "#26a69a") : cssVar("--color-red", "#ef5350");
    const textColor = cssVar("--text-secondary", "#787b86");
    const gridColor = cssVar("--border-subtle", "#2a2e39");

    const chart = createChart(containerRef.current, {
      height,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor,
        fontFamily: "JetBrains Mono, monospace",
      },
      grid: {
        vertLines: { color: gridColor },
        horzLines: { color: gridColor },
      },
      rightPriceScale: { borderColor: gridColor },
      timeScale: { borderColor: gridColor, timeVisible: false },
      crosshair: { mode: 1 },
    });
    chartRef.current = chart;

    // 蜡烛
    const candleSeries = chart.addCandlestickSeries({
      upColor,
      downColor,
      borderUpColor: upColor,
      borderDownColor: downColor,
      wickUpColor: upColor,
      wickDownColor: downColor,
    });

    const candleData = prices
      .filter((p) => p.open && p.high && p.low && p.close)
      .map((p) => ({
        time: p.date as Time,
        open: Number(p.open),
        high: Number(p.high),
        low: Number(p.low),
        close: Number(p.close),
      }));
    candleSeries.setData(candleData);

    // 成交量（底部独立刻度）
    const volSeries = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "vol",
    });
    chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    volSeries.setData(
      prices
        .filter((p) => p.volume != null)
        .map((p) => ({
          time: p.date as Time,
          value: Number(p.volume),
          color: Number(p.close) >= Number(p.open) ? `${upColor}80` : `${downColor}80`,
        })),
    );

    // 叠加 MA
    const lineSeriesList: ISeriesApi<"Line">[] = [];
    if (indicators?.indicators) {
      const dates = indicators.dates;
      const addLine = (values: (number | null)[], color: string) => {
        const series = chart.addLineSeries({ color, lineWidth: 1, priceLineVisible: false });
        series.setData(
          values
            .map((v, i) => ({ time: dates[i] as Time, value: v }))
            .filter((d) => d.value != null) as { time: Time; value: number }[],
        );
        lineSeriesList.push(series);
      };

      if (showMa && indicators.indicators.ma) {
        const maColors: Record<string, string> = {
          ma5: "#FF9800",
          ma10: "#2962FF",
          ma20: "#AB47BC",
          ma60: "#787B86",
        };
        Object.entries(indicators.indicators.ma).forEach(([k, vals]) => {
          addLine(vals, maColors[k] || "#787B86");
        });
      }
      if (showBoll && indicators.indicators.boll) {
        addLine(indicators.indicators.boll.upper, "#26A69A");
        addLine(indicators.indicators.boll.lower, "#EF5350");
      }
    }

    // 买卖点 marker
    if (transactions.length > 0) {
      const markers: SeriesMarker<Time>[] = transactions
        .slice()
        .sort((a, b) => a.trade_date.localeCompare(b.trade_date))
        .map((t) => ({
          time: t.trade_date as Time,
          position: t.type === "BUY" ? "belowBar" : "aboveBar",
          color: t.type === "BUY" ? upColor : downColor,
          shape: t.type === "BUY" ? "arrowUp" : "arrowDown",
          text: `${t.type === "BUY" ? "买" : "卖"} ${Number(t.quantity)}`,
        }));
      candleSeries.setMarkers(markers);
    }

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    handleResize();
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartRef.current = null;
    };
  }, [prices, indicators, transactions, height, showBoll, showMa, colorScheme]);

  if (prices.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-md border border-dashed border-border-subtle text-secondary"
        style={{ height }}
      >
        暂无行情数据，请先在管理页同步该股票
      </div>
    );
  }

  return <div ref={containerRef} className="w-full" />;
}
