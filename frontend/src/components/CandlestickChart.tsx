"use client";

import { useEffect, useRef } from "react";
import { createChart, CandlestickSeries, HistogramSeries, type IChartApi } from "lightweight-charts";

interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface Props {
  candles: Candle[];
  avgPrice?: number;
}

export function CandlestickChart({ candles, avgPrice }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current || candles.length === 0) return;

    // Clean up previous chart
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 400,
      layout: {
        background: { color: "transparent" },
        textColor: "#999",
      },
      grid: {
        vertLines: { color: "rgba(128,128,128,0.1)" },
        horzLines: { color: "rgba(128,128,128,0.1)" },
      },
      crosshair: {
        mode: 0,
      },
      rightPriceScale: {
        borderColor: "rgba(128,128,128,0.2)",
      },
      timeScale: {
        borderColor: "rgba(128,128,128,0.2)",
        timeVisible: false,
      },
    });
    chartRef.current = chart;

    // Candlestick series — Korean convention: up=red, down=blue
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#e31f26",
      downColor: "#1a56db",
      borderUpColor: "#e31f26",
      borderDownColor: "#1a56db",
      wickUpColor: "#e31f26",
      wickDownColor: "#1a56db",
      priceFormat: { type: "price", precision: 0, minMove: 1 },
    });
    candleSeries.setData(candles);

    // Volume histogram
    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    });
    chart.priceScale("volume").applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });
    volumeSeries.setData(
      candles.map((c) => ({
        time: c.time,
        value: c.volume,
        color: c.close >= c.open ? "rgba(227,31,38,0.3)" : "rgba(26,86,219,0.3)",
      }))
    );

    // Average price line
    if (avgPrice && avgPrice > 0) {
      candleSeries.createPriceLine({
        price: avgPrice,
        color: "#f59e0b",
        lineWidth: 1,
        lineStyle: 2, // dashed
        axisLabelVisible: true,
        title: "평균단가",
      });
    }

    chart.timeScale().fitContent();

    // Resize handler
    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartRef.current = null;
    };
  }, [candles, avgPrice]);

  if (candles.length === 0) {
    return (
      <div className="flex h-[400px] items-center justify-center text-sm text-muted-foreground">
        차트 데이터가 없습니다
      </div>
    );
  }

  return <div ref={containerRef} className="w-full" />;
}
