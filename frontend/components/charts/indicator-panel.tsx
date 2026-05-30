"use client";

import { ColorType, type IChartApi, type Time, createChart } from "lightweight-charts";
import { useEffect, useRef } from "react";

import type { IndicatorData } from "@/lib/hooks/use-stock";

interface IndicatorPanelProps {
  indicators: IndicatorData;
  type: "MACD" | "RSI";
  height?: number;
}

function cssVar(name: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

/** 副图面板：MACD（柱+DIF/DEA）或 RSI（含 30/70 参考线）。 */
export function IndicatorPanel({ indicators, type, height = 150 }: IndicatorPanelProps) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const gridColor = cssVar("--border-default", "#2a2a2a");
    const textColor = cssVar("--text-tertiary", "#8f8f8f");
    const green = cssVar("--color-green", "#2aa38e");
    const red = cssVar("--color-red", "#f05b5b");

    const chart = createChart(ref.current, {
      height,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor,
        fontFamily: "JetBrains Mono, monospace",
        fontSize: 11,
      },
      grid: { vertLines: { color: gridColor }, horzLines: { color: gridColor } },
      rightPriceScale: { borderColor: gridColor },
      timeScale: { borderColor: gridColor },
    });
    chartRef.current = chart;
    const dates = indicators.dates;

    if (type === "MACD" && indicators.indicators.macd) {
      const { dif, dea, hist } = indicators.indicators.macd;
      const histSeries = chart.addHistogramSeries();
      histSeries.setData(
        hist
          .map((v, i) => ({ time: dates[i] as Time, value: v, color: (v ?? 0) >= 0 ? green : red }))
          .filter((d) => d.value != null) as { time: Time; value: number; color: string }[],
      );
      const difSeries = chart.addLineSeries({ color: "#2962FF", lineWidth: 1, lastValueVisible: false });
      difSeries.setData(dif.map((v, i) => ({ time: dates[i] as Time, value: v })).filter((d) => d.value != null) as { time: Time; value: number }[]);
      const deaSeries = chart.addLineSeries({ color: "#FF9800", lineWidth: 1, lastValueVisible: false });
      deaSeries.setData(dea.map((v, i) => ({ time: dates[i] as Time, value: v })).filter((d) => d.value != null) as { time: Time; value: number }[]);
    }

    if (type === "RSI" && indicators.indicators.rsi) {
      const rsi = indicators.indicators.rsi.rsi14 || Object.values(indicators.indicators.rsi)[0];
      const series = chart.addLineSeries({ color: "#AB47BC", lineWidth: 1, lastValueVisible: false });
      series.setData(rsi.map((v, i) => ({ time: dates[i] as Time, value: v })).filter((d) => d.value != null) as { time: Time; value: number }[]);
      series.createPriceLine({ price: 70, color: red, lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "70" });
      series.createPriceLine({ price: 30, color: green, lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "30" });
    }

    chart.timeScale().fitContent();
    const onResize = () => ref.current && chart.applyOptions({ width: ref.current.clientWidth });
    onResize();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.remove();
      chartRef.current = null;
    };
  }, [indicators, type, height]);

  return <div ref={ref} className="w-full" />;
}
