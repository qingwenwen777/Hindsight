"use client";

import {
  ColorType,
  CrosshairMode,
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

interface PriceLine {
  price: number;
  color: string;
  title: string;
}

interface CandleChartProps {
  prices: PriceBar[];
  indicators?: IndicatorData;
  transactions?: Transaction[];
  /** 目标价/止损价水平线 */
  priceLines?: PriceLine[];
  height?: number;
  showBoll?: boolean;
  showMa?: boolean;
}

function cssVar(name: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

/**
 * K 线主图（TradingView 风格）—— lightweight-charts。
 * 蜡烛 + 成交量 + MA/布林带叠加 + 目标价/止损价水平线 + 自有交易买卖点 marker。
 * 涨跌色随 colorScheme（asia/western）切换。
 */
export function CandleChart({
  prices,
  indicators,
  transactions = [],
  priceLines = [],
  height = 450,
  showBoll = true,
  showMa = true,
}: CandleChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const colorScheme = useUiStore((s) => s.colorScheme);

  useEffect(() => {
    if (!containerRef.current || prices.length === 0) return;

    const green = cssVar("--color-green", "#2aa38e");
    const red = cssVar("--color-red", "#f05b5b");
    const upColor = colorScheme === "asia" ? red : green;
    const downColor = colorScheme === "asia" ? green : red;
    const textColor = cssVar("--text-tertiary", "#8f8f8f");
    const gridColor = cssVar("--border-default", "#2a2a2a");
    const warnColor = cssVar("--warn", "#d9a441");

    const chart = createChart(containerRef.current, {
      height,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor,
        fontFamily: "JetBrains Mono, monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: gridColor, style: 0 },
        horzLines: { color: gridColor, style: 0 },
      },
      rightPriceScale: { borderColor: gridColor },
      timeScale: { borderColor: gridColor, timeVisible: false, rightOffset: 6 },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: cssVar("--border-strong", "#4a4a4a"), labelBackgroundColor: cssVar("--bg-elevated", "#2b2b2b") },
        horzLine: { color: cssVar("--border-strong", "#4a4a4a"), labelBackgroundColor: cssVar("--bg-elevated", "#2b2b2b") },
      },
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

    // 目标价/止损价水平线
    for (const pl of priceLines) {
      candleSeries.createPriceLine({
        price: pl.price,
        color: pl.color,
        lineWidth: 1,
        lineStyle: 2, // dashed
        axisLabelVisible: true,
        title: pl.title,
      });
    }

    // 成交量（底部独立刻度）
    const volSeries = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "vol",
    });
    chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    volSeries.setData(
      prices
        .filter((p) => p.volume != null)
        .map((p) => ({
          time: p.date as Time,
          value: Number(p.volume),
          color: Number(p.close) >= Number(p.open) ? `${upColor}55` : `${downColor}55`,
        })),
    );

    // 叠加 MA / 布林带
    const lineSeriesList: ISeriesApi<"Line">[] = [];
    if (indicators?.indicators) {
      const dates = indicators.dates;
      const addLine = (values: (number | null)[], color: string, width = 1) => {
        const series = chart.addLineSeries({
          color,
          lineWidth: width as 1 | 2 | 3,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        });
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
        addLine(indicators.indicators.boll.upper, warnColor);
        addLine(indicators.indicators.boll.lower, warnColor);
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
          text: `${t.type === "BUY" ? "B" : "S"} ${Number(t.quantity)}`,
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
  }, [prices, indicators, transactions, priceLines, height, showBoll, showMa, colorScheme]);

  if (prices.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-md border border-border-default bg-base text-tertiary"
        style={{ height }}
      >
        暂无行情数据，请先在管理页同步该股票
      </div>
    );
  }

  return <div ref={containerRef} className="w-full" />;
}
