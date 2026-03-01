"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { useMarketStore } from "@/stores/market-store";
import { useUIStore } from "@/stores/ui-store";
import type { TickData } from "@/types/market";
import {
  Database,
  Download,
  CheckCircle2,
  Loader2,
  ChevronDown,
  RefreshCw,
  Clock,
} from "lucide-react";

interface LoadState {
  status: "idle" | "loading" | "complete" | "error" | "cached";
  percent: number;
  loaded: number;
  total: number;
  currentSymbol: string;
  message: string;
  lastUpdated: string | null;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export function DataLoader() {
  const preset = useUIStore((s) => s.preset);
  const setPreset = useUIStore((s) => s.setPreset);
  const years = useUIStore((s) => s.years);
  const setYears = useUIStore((s) => s.setYears);
  const [expanded, setExpanded] = useState(false);
  const [state, setState] = useState<LoadState>({
    status: "idle",
    percent: 0,
    loaded: 0,
    total: 0,
    currentSymbol: "",
    message: "",
    lastUpdated: null,
  });
  const abortRef = useRef<AbortController | null>(null);
  const updateTick = useMarketStore((s) => s.updateTick);
  const bulkUpdateTicks = useMarketStore((s) => s.bulkUpdateTicks);
  const initDone = useRef(false);

  // ── Auto-load from DB cache on mount ──────────────────────
  useEffect(() => {
    if (initDone.current) return;
    initDone.current = true;

    (async () => {
      try {
        const res = await fetch(`${API_BASE}/cached-data?preset=${preset}`);
        if (!res.ok) return;
        const data = await res.json();

        if (data.ticks && data.ticks.length > 0) {
          bulkUpdateTicks(data.ticks as TickData[]);
          setState({
            status: "cached",
            percent: 100,
            loaded: data.symbol_count,
            total: data.symbol_count,
            currentSymbol: "",
            message: `Loaded ${data.symbol_count} symbols from cache`,
            lastUpdated: data.last_updated,
          });
          setExpanded(false);
        } else {
          setExpanded(true);
        }
      } catch {
        // Backend not ready — show loader expanded
        setExpanded(true);
      }
    })();
  }, [preset, bulkUpdateTicks]);

  const handleEvent = useCallback(
    (event: string, data: Record<string, unknown>) => {
      switch (event) {
        case "start":
          setState((s) => ({
            ...s,
            total: data.total as number,
            message: `Loading ${data.total} symbols x ${data.years} years...`,
          }));
          break;

        case "progress":
          setState((s) => ({
            ...s,
            loaded: data.loaded as number,
            percent: data.percent as number,
            currentSymbol: data.symbol as string,
            message: data.status as string,
          }));
          break;

        case "tick": {
          const tick: TickData = {
            symbol: data.symbol as string,
            price: data.price as number,
            change: data.change as number,
            changePct: data.changePct as number,
            volume: data.volume as number,
            high: data.high as number,
            low: data.low as number,
            open: data.open as number,
            ceiling: data.ceiling as number,
            floor: data.floor as number,
            reference: data.reference as number,
            timestamp: data.timestamp as number,
          };
          updateTick(tick);
          break;
        }

        case "complete":
          setState({
            status: "complete",
            percent: 100,
            loaded: data.loaded as number,
            total: data.total as number,
            currentSymbol: "",
            message: data.message as string,
            lastUpdated: (data.last_updated as string) ?? null,
          });
          break;
      }
    },
    [updateTick]
  );

  // ── Stream-load from API ──────────────────────────────────
  const handleLoad = useCallback(async () => {
    if (state.status === "loading") {
      abortRef.current?.abort();
      setState((s) => ({ ...s, status: "idle", message: "Cancelled" }));
      return;
    }

    const controller = new AbortController();
    abortRef.current = controller;

    setState({
      status: "loading",
      percent: 0,
      loaded: 0,
      total: 0,
      currentSymbol: "",
      message: "Connecting...",
      lastUpdated: state.lastUpdated,
    });

    try {
      const url = `${API_BASE}/load-data?preset=${preset}&years=${years}`;
      const res = await fetch(url, { signal: controller.signal });

      if (!res.ok || !res.body) {
        throw new Error(`HTTP ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        let eventType = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith("data: ") && eventType) {
            try {
              const data = JSON.parse(line.slice(6));
              handleEvent(eventType, data);
            } catch {
              // skip parse errors
            }
            eventType = "";
          }
        }
      }
    } catch (e) {
      if ((e as Error).name !== "AbortError") {
        setState((s) => ({
          ...s,
          status: "error",
          message: `Error: ${(e as Error).message}`,
        }));
      }
    }
  }, [preset, years, state.status, state.lastUpdated, handleEvent]);

  const isLoading = state.status === "loading";
  const isDone = state.status === "complete" || state.status === "cached";

  return (
    <div className="overflow-hidden rounded-lg border border-zinc-800 bg-zinc-900">
      {/* Header — always visible */}
      <button
        onClick={() => setExpanded((e) => !e)}
        className="flex w-full items-center justify-between px-3 py-2.5 transition-colors hover:bg-zinc-800/50 sm:px-4"
      >
        <div className="flex min-w-0 items-center gap-2">
          <Database className="h-4 w-4 text-emerald-400" />
          <span className="text-xs font-medium uppercase tracking-wider text-zinc-400">
            Market Data
          </span>
          {isDone && (
            <span className="flex items-center gap-1 text-xs text-emerald-400">
              <CheckCircle2 className="h-3 w-3" />
              {state.loaded} symbols
            </span>
          )}
          {state.lastUpdated && (
            <span className="ml-1 hidden items-center gap-1 text-[10px] text-zinc-600 sm:flex">
              <Clock className="h-3 w-3" />
              Cập nhật: {state.lastUpdated}
            </span>
          )}
        </div>
        <ChevronDown
          className={`h-4 w-4 text-zinc-500 transition-transform ${expanded ? "rotate-180" : ""}`}
        />
      </button>

      {/* Expandable body */}
      {expanded && (
        <div className="space-y-3 border-t border-zinc-800 px-3 pb-4 pt-3 sm:px-4">
          {/* Row: Preset + Years */}
          <div className="flex flex-col gap-3 lg:flex-row lg:items-end">
            {/* Preset selector */}
            <div className="w-full lg:flex-1">
              <label className="mb-1 block text-[11px] font-medium text-zinc-500 uppercase">
                Danh sách
              </label>
              <div className="flex rounded-md overflow-hidden border border-zinc-700">
                <button
                  onClick={() => setPreset("VN30")}
                  disabled={isLoading}
                  className={`flex-1 px-3 py-1.5 text-xs font-semibold transition-colors ${preset === "VN30"
                    ? "bg-emerald-600 text-white"
                    : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
                    }`}
                >
                  VN30
                </button>
                <button
                  onClick={() => setPreset("TOP100")}
                  disabled={isLoading}
                  className={`flex-1 px-3 py-1.5 text-xs font-semibold transition-colors ${preset === "TOP100"
                    ? "bg-amber-600 text-white"
                    : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
                    }`}
                >
                  Top 100
                </button>
              </div>
            </div>

            {/* Years slider */}
            <div className="w-full lg:flex-1">
              <label className="mb-1 block text-[11px] font-medium text-zinc-500 uppercase">
                Dữ liệu: {years} năm
              </label>
              <input
                type="range"
                min={1}
                max={10}
                value={years}
                onChange={(e) => setYears(Number(e.target.value))}
                disabled={isLoading}
                className="w-full h-1.5 appearance-none rounded-full bg-zinc-700 accent-emerald-500 cursor-pointer disabled:opacity-50"
              />
              <div className="flex justify-between mt-0.5">
                <span className="text-[10px] text-zinc-600">1Y</span>
                <span className="text-[10px] text-zinc-600">5Y</span>
                <span className="text-[10px] text-zinc-600">10Y</span>
              </div>
            </div>

            {/* Load / Refresh button */}
            <button
              onClick={handleLoad}
              className={`flex w-full items-center justify-center gap-1.5 rounded-md px-4 py-2 text-xs font-semibold transition-all lg:w-auto lg:py-1.5 ${
                isLoading
                  ? "bg-red-600/80 text-white hover:bg-red-600"
                  : isDone
                    ? "bg-zinc-700 text-zinc-200 hover:bg-zinc-600"
                    : "bg-emerald-600 text-white hover:bg-emerald-500"
              }`}
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Stop
                </>
              ) : isDone ? (
                <>
                  <RefreshCw className="h-3.5 w-3.5" />
                  Update
                </>
              ) : (
                <>
                  <Download className="h-3.5 w-3.5" />
                  Load
                </>
              )}
            </button>
          </div>

          {/* Progress bar */}
          {isLoading && (
            <div className="space-y-1">
              <div className="relative h-2 overflow-hidden rounded-full bg-zinc-800">
                <div
                  className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-emerald-600 to-emerald-400 transition-all duration-300"
                  style={{ width: `${state.percent}%` }}
                />
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent animate-[shimmer_1.5s_infinite]" />
              </div>
              <div className="flex items-center justify-between">
                <span className="pr-2 text-[11px] text-zinc-500">
                  {state.currentSymbol && (
                    <span className="text-emerald-400 font-mono">
                      {state.currentSymbol}
                    </span>
                  )}
                  {state.currentSymbol && " — "}
                  {state.message}
                </span>
                <span className="text-[11px] font-mono text-zinc-400">
                  {state.loaded}/{state.total} ({Math.round(state.percent)}%)
                </span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
