"use client";

import { useEffect, useRef, useCallback } from "react";
import {
  createChart,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type Time,
} from "lightweight-charts";
import { useMarketStore } from "@/stores/market-store";
import { useUIStore } from "@/stores/ui-store";

const API_BASE = "http://localhost:8000/api";

export function TradingChart() {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const activeSymbol = useUIStore((s) => s.activeSymbol);
  const prevSymbolRef = useRef(activeSymbol);

  // Initialize chart ONCE
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: "#09090b" },
        textColor: "#a1a1aa",
      },
      grid: {
        vertLines: { color: "#27272a33" },
        horzLines: { color: "#27272a33" },
      },
      crosshair: { mode: 0 },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        borderColor: "#27272a",
      },
      rightPriceScale: { borderColor: "#27272a" },
    });

    const series = chart.addCandlestickSeries({
      upColor: "#34d399",
      downColor: "#f87171",
      borderVisible: false,
      wickUpColor: "#34d399",
      wickDownColor: "#f87171",
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        const { width, height } = entry.contentRect;
        chart.applyOptions({ width, height });
      }
    });
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chart.remove();
    };
  }, []);

  // Fetch candles from backend for a symbol
  const loadCandles = useCallback(async (symbol: string) => {
    const series = seriesRef.current;
    if (!series) return;

    try {
      const res = await fetch(`${API_BASE}/candles/${symbol}?limit=500`);
      if (!res.ok) {
        // Fallback to generated data if backend doesn't have candles
        generateFallbackData(symbol, series);
        return;
      }

      const data = await res.json();
      if (data.candles && data.candles.length > 0) {
        const formatted: CandlestickData<Time>[] = data.candles.map(
          (c: { time: number; open: number; high: number; low: number; close: number }) => ({
            time: c.time as Time,
            open: c.open,
            high: c.high,
            low: c.low,
            close: c.close,
          })
        );
        series.setData(formatted);
        chartRef.current?.timeScale().fitContent();
      } else {
        generateFallbackData(symbol, series);
      }
    } catch {
      generateFallbackData(symbol, series);
    }
  }, []);

  // Fallback: generate sample candles client-side
  const generateFallbackData = useCallback(
    (symbol: string, series: ISeriesApi<"Candlestick">) => {
      const now = Math.floor(Date.now() / 1000);
      const sampleData: CandlestickData<Time>[] = [];

      // Use symbol hash for deterministic but unique data
      let seed = 0;
      for (let i = 0; i < symbol.length; i++) {
        seed = (seed * 31 + symbol.charCodeAt(i)) | 0;
      }
      const rng = () => {
        seed = (seed * 1103515245 + 12345) & 0x7fffffff;
        return seed / 0x7fffffff;
      };

      let price = 30 + rng() * 120;
      for (let i = 200; i >= 0; i--) {
        const time = (now - i * 86400) as Time;
        const drift = (rng() - 0.48) * 4;
        price = Math.max(5, price + drift);
        const open = price + (rng() - 0.5) * 3;
        const close = open + (rng() - 0.5) * 4;
        const high = Math.max(open, close) + rng() * 2;
        const low = Math.min(open, close) - rng() * 2;
        sampleData.push({
          time,
          open: Math.round(open * 100) / 100,
          high: Math.round(high * 100) / 100,
          low: Math.round(low * 100) / 100,
          close: Math.round(close * 100) / 100,
        });
      }

      series.setData(sampleData);
      chartRef.current?.timeScale().fitContent();
    },
    []
  );

  // Load candles when symbol changes
  useEffect(() => {
    loadCandles(activeSymbol);
    prevSymbolRef.current = activeSymbol;
  }, [activeSymbol, loadCandles]);

  // Subscribe to real-time candle updates
  useEffect(() => {
    const unsubscribe = useMarketStore.subscribe(
      (state) => state.candles[activeSymbol],
      (candle) => {
        if (candle && seriesRef.current) {
          seriesRef.current.update({
            time: candle.time as Time,
            open: candle.open,
            high: candle.high,
            low: candle.low,
            close: candle.close,
          });
        }
      }
    );
    return unsubscribe;
  }, [activeSymbol]);

  return (
    <div className="relative h-full w-full rounded-md bg-zinc-950">
      <div className="absolute left-3 top-2 z-10 flex items-center gap-2">
        <span className="text-sm font-bold text-amber-300">
          {activeSymbol}
        </span>
        <span className="text-xs text-zinc-600">· 1D</span>
      </div>
      <div ref={containerRef} className="h-full w-full" />
    </div>
  );
}
