"use client";

/**
 * SymbolPopup — Modal hiển thị biểu đồ + chỉ báo kỹ thuật khi click vào mã CP.
 * ★ Inspired by fireant.vn/dashboard/content/symbols/VN30 popup style.
 * ★ Hiển thị: Chart nến, RSI, MACD, Bollinger, MA, Volume, thông tin cơ bản.
 */

import { useEffect, useRef, useCallback, useState } from "react";
import { X, TrendingUp, TrendingDown, BarChart3, Activity, ExternalLink } from "lucide-react";
import {
  createChart,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type Time,
} from "lightweight-charts";
import { useUIStore } from "@/stores/ui-store";
import { useMarketStore } from "@/stores/market-store";
import { cn } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(v: number | undefined, decimals = 2): string {
  if (v == null) return "—";
  return v.toLocaleString("vi-VN", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function fmtPct(v: number | undefined): string {
  if (v == null) return "—";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(2)}%`;
}

function fmtVol(v: number | undefined): string {
  if (v == null) return "—";
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`;
  return v.toString();
}

// ── Indicator Row ─────────────────────────────────────────────────────────────

function IndicatorRow({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex items-center justify-between border-b border-zinc-800/40 py-1 last:border-0">
      <span className="text-xs text-zinc-500 sm:text-[11px]">{label}</span>
      <span className={cn("text-xs font-mono font-semibold sm:text-[11px]", color ?? "text-zinc-200")}>{value}</span>
    </div>
  );
}

// ── Candlestick Chart ─────────────────────────────────────────────────────────

function PopupChart({ symbol }: { symbol: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  const generateFallback = useCallback((sym: string, series: ISeriesApi<"Candlestick">) => {
    const now = Math.floor(Date.now() / 1000);
    let seed = 0;
    for (let i = 0; i < sym.length; i++) seed = (seed * 31 + sym.charCodeAt(i)) | 0;
    const rng = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
    let price = 30 + rng() * 120;
    const data: CandlestickData<Time>[] = [];
    for (let i = 200; i >= 0; i--) {
      const time = (now - i * 86400) as Time;
      price = Math.max(5, price + (rng() - 0.48) * 4);
      const open = price + (rng() - 0.5) * 3;
      const close = open + (rng() - 0.5) * 4;
      data.push({
        time, open: Math.round(open * 100) / 100,
        high: Math.round((Math.max(open, close) + rng() * 2) * 100) / 100,
        low: Math.round((Math.min(open, close) - rng() * 2) * 100) / 100,
        close: Math.round(close * 100) / 100,
      });
    }
    series.setData(data);
    chartRef.current?.timeScale().fitContent();
  }, []);

  const loadCandles = useCallback(async (sym: string) => {
    const series = seriesRef.current;
    if (!series) return;
    try {
      const res = await fetch(`${API_BASE}/candles/${sym}?limit=300`);
      if (!res.ok) { generateFallback(sym, series); return; }
      const data = await res.json();
      if (data.candles?.length > 0) {
        series.setData(data.candles.map((c: { time: number; open: number; high: number; low: number; close: number }) => ({
          time: c.time as Time, open: c.open, high: c.high, low: c.low, close: c.close,
        })));
        chartRef.current?.timeScale().fitContent();
      } else {
        generateFallback(sym, series);
      }
    } catch { generateFallback(sym, series); }
  }, [generateFallback]);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      layout: { background: { color: "#09090b" }, textColor: "#a1a1aa" },
      grid: { vertLines: { color: "#27272a22" }, horzLines: { color: "#27272a22" } },
      crosshair: { mode: 1 },
      timeScale: { timeVisible: true, secondsVisible: false, borderColor: "#27272a" },
      rightPriceScale: { borderColor: "#27272a" },
    });
    const series = chart.addCandlestickSeries({
      upColor: "#34d399", downColor: "#f87171",
      borderVisible: false, wickUpColor: "#34d399", wickDownColor: "#f87171",
    });
    chartRef.current = chart;
    seriesRef.current = series;
    const observer = new ResizeObserver((entries) => {
      const e = entries[0];
      if (e) chart.applyOptions({ width: e.contentRect.width, height: e.contentRect.height });
    });
    observer.observe(containerRef.current);
    return () => { observer.disconnect(); chart.remove(); };
  }, []);

  useEffect(() => { loadCandles(symbol); }, [symbol, loadCandles]);

  return <div ref={containerRef} className="h-full w-full" />;
}

// ── Main Popup Component ──────────────────────────────────────────────────────

export function SymbolPopup() {
  const { symbolPopupOpen, symbolPopupSymbol, closeSymbolPopup } = useUIStore();
  const ticks = useMarketStore((s) => s.ticks);
  const [technicals, setTechnicals] = useState<Record<string, number | string> | null>(null);

  const symbol = symbolPopupSymbol ?? "";
  const tick = ticks[symbol];

  // Fetch technical indicators when popup opens
  useEffect(() => {
    if (!symbolPopupOpen || !symbol) return;
    setTechnicals(null);
    fetch(`${API_BASE}/company/${symbol}`)
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (data?.technicals) setTechnicals(data.technicals);
      })
      .catch(() => null);
  }, [symbolPopupOpen, symbol]);

  // Close on Escape key
  useEffect(() => {
    if (!symbolPopupOpen) return;
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") closeSymbolPopup(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [symbolPopupOpen, closeSymbolPopup]);

  if (!symbolPopupOpen || !symbol) return null;

  const isUp = (tick?.change ?? 0) > 0;
  const isDown = (tick?.change ?? 0) < 0;
  const priceColor = isUp ? "text-emerald-400" : isDown ? "text-rose-400" : "text-amber-300";

  const t = technicals as Record<string, number> | null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm"
        onClick={closeSymbolPopup}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex flex-col overflow-hidden border-zinc-700 bg-zinc-950 shadow-2xl sm:inset-x-4 sm:bottom-[5vh] sm:top-[5vh] sm:mx-auto sm:max-w-5xl sm:rounded-xl sm:border">
        {/* ── Header ── */}
        <div className="flex shrink-0 flex-wrap items-start justify-between gap-2 border-b border-zinc-800 px-3 py-3 sm:px-5">
          <div className="min-w-0 flex-1">
            {/* Symbol + name */}
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-amber-300 sm:text-xl">{symbol}</h2>
                <span className="text-xs text-zinc-500 bg-zinc-800 px-2 py-0.5 rounded">HOSE</span>
              </div>
            </div>

            {/* Price info */}
            {tick && (
              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 sm:mt-0 sm:ml-4 sm:flex-nowrap">
                <span className={cn("text-xl font-mono font-bold tabular-nums sm:text-2xl", priceColor)}>
                  {fmt(tick.price)}
                </span>
                <div className="flex flex-col">
                  <span className={cn("text-sm font-mono tabular-nums", priceColor)}>
                    {isUp ? "▲" : isDown ? "▼" : "—"} {fmt(Math.abs(tick.change ?? 0))}
                  </span>
                  <span className={cn("text-xs font-mono tabular-nums", priceColor)}>
                    {fmtPct(tick.changePct)}
                  </span>
                </div>
                <div className="flex flex-col text-xs text-zinc-500 ml-2">
                  <span>KL: <span className="text-zinc-300 font-mono">{fmtVol(tick.volume)}</span></span>
                  <span>Trần: <span className="text-fuchsia-400 font-mono">{fmt(tick.ceiling)}</span></span>
                  <span>Sàn: <span className="text-cyan-400 font-mono">{fmt(tick.floor)}</span></span>
                </div>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* Link to full page */}
            <a
              href={`/company/${symbol}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 rounded-lg bg-zinc-800 px-2.5 py-1.5 text-xs text-zinc-400 transition-colors hover:bg-zinc-700 hover:text-zinc-200 sm:px-3"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Xem đầy đủ</span>
              <span className="sm:hidden">Xem</span>
            </a>
            <button
              onClick={closeSymbolPopup}
              className="flex h-8 w-8 items-center justify-center rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-zinc-200 transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* ── Body: Chart + Indicators ── */}
        <div className="flex flex-1 min-h-0 flex-col sm:flex-row">
          {/* Chart — takes most space */}
          <div className="min-h-[42vh] min-w-0 flex-1 bg-zinc-950 sm:min-h-0">
            <PopupChart symbol={symbol} />
          </div>

          {/* Right panel: Technical indicators */}
          <div className="w-full shrink-0 overflow-y-auto border-t border-zinc-800 bg-zinc-900/50 sm:w-56 sm:border-l sm:border-t-0">
            {/* Price levels */}
            {tick && (
              <div className="px-3 py-2 border-b border-zinc-800">
                <p className="mb-1.5 text-[10px] font-bold uppercase tracking-wider text-zinc-500">Giá hôm nay</p>
                <IndicatorRow label="Mở cửa" value={fmt(tick.open)} />
                <IndicatorRow label="Cao nhất" value={fmt(tick.high)} color="text-emerald-400" />
                <IndicatorRow label="Thấp nhất" value={fmt(tick.low)} color="text-rose-400" />
                <IndicatorRow label="Tham chiếu" value={fmt(tick.reference)} color="text-amber-300" />
              </div>
            )}

            {/* Technical indicators */}
            <div className="px-3 py-2 border-b border-zinc-800">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <Activity className="h-3 w-3 text-emerald-400" />
                  <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">Chỉ báo kỹ thuật</p>
              </div>
              {t ? (
                <>
                  <IndicatorRow
                    label="RSI (14)"
                    value={fmt(t.rsi_14 ?? 0, 1)}
                    color={(t.rsi_14 ?? 0) >= 70 ? "text-rose-400" : (t.rsi_14 ?? 0) <= 30 ? "text-emerald-400" : "text-amber-300"}
                  />
                  <IndicatorRow
                    label="MACD"
                    value={fmt(t.macd ?? 0, 3)}
                    color={(t.macd ?? 0) > (t.macd_signal ?? 0) ? "text-emerald-400" : "text-rose-400"}
                  />
                  <IndicatorRow label="Signal" value={fmt(t.macd_signal ?? 0, 3)} />
                  <IndicatorRow label="MA20" value={fmt(t.ma_20 ?? 0)} />
                  <IndicatorRow label="MA50" value={fmt(t.ma_50 ?? 0)} />
                  <IndicatorRow label="MA200" value={fmt(t.ma_200 ?? 0)} />
                  <IndicatorRow label="BB Upper" value={fmt(t.bollinger_upper ?? 0)} color="text-emerald-400/70" />
                  <IndicatorRow label="BB Lower" value={fmt(t.bollinger_lower ?? 0)} color="text-rose-400/70" />
                  <IndicatorRow
                    label="ADX"
                    value={fmt(t.adx ?? 0, 1)}
                    color={(t.adx ?? 0) > 25 ? "text-amber-300" : "text-zinc-400"}
                  />
                  <IndicatorRow label="ATR (14)" value={fmt(t.atr_14 ?? 0)} />
                  <IndicatorRow label="CCI" value={fmt(t.cci ?? 0, 1)} />
                  <IndicatorRow
                    label="Stoch %K"
                    value={fmt(t.stochastic_k ?? 0, 1)}
                    color={(t.stochastic_k ?? 0) >= 80 ? "text-rose-400" : (t.stochastic_k ?? 0) <= 20 ? "text-emerald-400" : "text-zinc-300"}
                  />
                  <IndicatorRow
                    label="OBV Trend"
                    value={String(t.obv_trend ?? "—")}
                    color={String(t.obv_trend) === "bullish" ? "text-emerald-400" : String(t.obv_trend) === "bearish" ? "text-rose-400" : "text-zinc-400"}
                  />
                </>
              ) : (
                <div className="flex items-center justify-center py-4">
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-zinc-700 border-t-emerald-400" />
                </div>
              )}
            </div>

            {/* Support / Resistance */}
            {t && (
              <div className="px-3 py-2">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <BarChart3 className="h-3 w-3 text-emerald-400" />
                  <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">Hỗ trợ / Kháng cự</p>
                </div>
                <div className="flex items-center justify-between rounded-lg bg-zinc-800/50 px-2 py-1.5 mb-1">
                  <div className="flex items-center gap-1 text-xs sm:text-[11px]">
                    <TrendingDown className="h-3 w-3 text-rose-400" />
                    <span className="text-zinc-500">Hỗ trợ</span>
                  </div>
                  <span className="font-mono text-xs font-semibold text-rose-400 sm:text-[11px]">{fmt(t.support)}</span>
                </div>
                <div className="flex items-center justify-between rounded-lg bg-zinc-800/50 px-2 py-1.5">
                  <div className="flex items-center gap-1 text-xs sm:text-[11px]">
                    <TrendingUp className="h-3 w-3 text-emerald-400" />
                    <span className="text-zinc-500">Kháng cự</span>
                  </div>
                  <span className="font-mono text-xs font-semibold text-emerald-400 sm:text-[11px]">{fmt(t.resistance)}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
