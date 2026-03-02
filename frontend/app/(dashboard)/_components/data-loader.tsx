"use client";

import { useState, useCallback, useRef, useEffect, useMemo } from "react";
import { useMarketStore } from "@/stores/market-store";
import { useUIStore } from "@/stores/ui-store";
import type { TickData } from "@/types/market";
import { Database, Download, CheckCircle2, Loader2, ChevronDown, RefreshCw, Clock, Square } from "lucide-react";

type LoaderStatus = "no_cache" | "loading" | "loaded" | "updating" | "error" | "cancelled";
type LoaderMode = "load" | "update";

interface LoadState {
  status: LoaderStatus;
  percent: number;
  loaded: number;
  total: number;
  currentSymbol: string;
  message: string;
  lastUpdated: string | null;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

const STATUS_LABEL: Record<LoaderStatus, string> = {
  no_cache: "No cache",
  loading: "Loading data",
  loaded: "Loaded",
  updating: "Updating",
  error: "Error",
  cancelled: "Cancelled",
};

export function DataLoader() {
  const preset = useUIStore((s) => s.preset);
  const setPreset = useUIStore((s) => s.setPreset);
  const years = useUIStore((s) => s.years);
  const setYears = useUIStore((s) => s.setYears);

  const replaceTicks = useMarketStore((s) => s.replaceTicks);
  const clearTicks = useMarketStore((s) => s.clearTicks);
  const updateTick = useMarketStore((s) => s.updateTick);
  const ticks = useMarketStore((s) => s.ticks);

  const [expanded, setExpanded] = useState(false);
  const [state, setState] = useState<LoadState>({
    status: "no_cache",
    percent: 0,
    loaded: 0,
    total: 0,
    currentSymbol: "",
    message: "No cache. Bấm Load để nạp dữ liệu.",
    lastUpdated: null,
  });
  const abortRef = useRef<AbortController | null>(null);

  const tickCount = useMemo(() => Object.keys(ticks).length, [ticks]);
  const isBusy = state.status === "loading" || state.status === "updating";
  const canUpdate = tickCount > 0 && !isBusy;

  const handleEvent = useCallback(
    (event: string, data: Record<string, unknown>, mode: LoaderMode) => {
      switch (event) {
        case "start":
          setState((s) => ({
            ...s,
            status: mode === "load" ? "loading" : "updating",
            total: Number(data.total ?? 0),
            message:
              mode === "load"
                ? `Loading ${data.total ?? 0} symbols x ${data.years ?? years} years...`
                : `Updating ${data.total ?? 0} cached symbols...`,
          }));
          break;

        case "progress":
          setState((s) => ({
            ...s,
            loaded: Number(data.loaded ?? 0),
            percent: Number(data.percent ?? 0),
            currentSymbol: String(data.symbol ?? ""),
            message: String(data.status ?? (mode === "load" ? "Loading data..." : "Updating data...")),
          }));
          break;

        case "tick": {
          const tick: TickData = {
            symbol: String(data.symbol ?? ""),
            price: Number(data.price ?? 0),
            change: Number(data.change ?? 0),
            changePct: Number(data.changePct ?? 0),
            volume: Number(data.volume ?? 0),
            high: Number(data.high ?? 0),
            low: Number(data.low ?? 0),
            open: Number(data.open ?? 0),
            ceiling: Number(data.ceiling ?? 0),
            floor: Number(data.floor ?? 0),
            reference: Number(data.reference ?? 0),
            timestamp: Number(data.timestamp ?? Date.now()),
          };
          updateTick(tick);
          break;
        }

        case "error":
          setState((s) => ({
            ...s,
            status: "error",
            message: String(data.message ?? "Operation failed"),
          }));
          break;

        case "complete":
          setState({
            status: "loaded",
            percent: 100,
            loaded: Number(data.loaded ?? 0),
            total: Number(data.total ?? 0),
            currentSymbol: "",
            message: String(data.message ?? "Loaded"),
            lastUpdated: (data.last_updated as string) ?? null,
          });
          break;
      }
    },
    [updateTick, years]
  );

  const runStream = useCallback(
    async (mode: LoaderMode) => {
      if (abortRef.current) return;

      const controller = new AbortController();
      abortRef.current = controller;

      setState((prev) => ({
        ...prev,
        status: mode === "load" ? "loading" : "updating",
        percent: 0,
        loaded: 0,
        total: 0,
        currentSymbol: "",
        message: mode === "load" ? "Loading data..." : "Updating cached data...",
      }));

      if (mode === "load") {
        clearTicks();
      }

      try {
        const url =
          mode === "load"
            ? `${API_BASE}/load-data?preset=${preset}&years=${years}`
            : `${API_BASE}/update-data?preset=${preset}`;

        const res = await fetch(url, { signal: controller.signal });
        if (!res.ok || !res.body) {
          throw new Error(`HTTP ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let eventType = "";
        let sawTerminalEvent = false;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith("data: ") && eventType) {
              const parsed = JSON.parse(line.slice(6)) as Record<string, unknown>;
              handleEvent(eventType, parsed, mode);
              if (eventType === "complete" || eventType === "error") {
                sawTerminalEvent = true;
              }
              eventType = "";
            }
          }
        }

        if (!sawTerminalEvent) {
          setState((s) => ({
            ...s,
            status: "error",
            message: "Data stream interrupted. Please retry Load/Update.",
          }));
        }
      } catch (e) {
        if ((e as Error).name === "AbortError") {
          setState((s) => ({
            ...s,
            status: "cancelled",
            message: "Cancelled by user.",
          }));
        } else {
          setState((s) => ({
            ...s,
            status: "error",
            message: `Error: ${(e as Error).message}`,
          }));
        }
      } finally {
        if (abortRef.current === controller) {
          abortRef.current = null;
        }
      }
    },
    [preset, years, handleEvent, clearTicks]
  );

  const handleLoad = useCallback(() => {
    if (isBusy) return;
    void runStream("load");
  }, [isBusy, runStream]);

  const handleUpdate = useCallback(() => {
    if (!canUpdate) return;
    void runStream("update");
  }, [canUpdate, runStream]);

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  // Restore from cache only. Never auto-load.
  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const res = await fetch(`${API_BASE}/cached-data?preset=${preset}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (cancelled) return;

        if (Array.isArray(data.ticks) && data.ticks.length > 0) {
          replaceTicks(data.ticks as TickData[]);
          setState({
            status: "loaded",
            percent: 100,
            loaded: Number(data.symbol_count ?? 0),
            total: Number(data.symbol_count ?? 0),
            currentSymbol: "",
            message: `Loaded ${data.symbol_count ?? 0} symbols from cache`,
            lastUpdated: (data.last_updated as string) ?? null,
          });
          setExpanded(false);
        } else {
          clearTicks();
          setState({
            status: "no_cache",
            percent: 0,
            loaded: 0,
            total: 0,
            currentSymbol: "",
            message: "No cache. Bấm Load để nạp dữ liệu.",
            lastUpdated: null,
          });
          setExpanded(true);
        }
      } catch {
        if (cancelled) return;
        clearTicks();
        setState({
          status: "error",
          percent: 0,
          loaded: 0,
          total: 0,
          currentSymbol: "",
          message: "Error reading cache. Please retry.",
          lastUpdated: null,
        });
        setExpanded(true);
      }
    })();

    return () => {
      cancelled = true;
      abortRef.current?.abort();
    };
  }, [preset, replaceTicks, clearTicks]);

  return (
    <div className="overflow-hidden rounded-lg border border-zinc-800 bg-zinc-900">
      <button
        onClick={() => setExpanded((e) => !e)}
        className="flex w-full items-center justify-between px-3 py-2.5 transition-colors hover:bg-zinc-800/50 sm:px-4"
      >
        <div className="flex min-w-0 items-center gap-2">
          <Database className="h-4 w-4 text-emerald-400" />
          <span className="text-xs font-medium uppercase tracking-wider text-zinc-400">Market Data</span>
          {state.status === "loaded" && (
            <span className="flex items-center gap-1 text-xs text-emerald-400">
              <CheckCircle2 className="h-3 w-3" />
              {state.loaded} symbols
            </span>
          )}
          <span className="rounded border border-zinc-700/80 bg-zinc-950/70 px-1.5 py-0.5 text-[10px] uppercase text-zinc-400">
            {STATUS_LABEL[state.status]}
          </span>
          {state.lastUpdated && (
            <span className="ml-1 hidden items-center gap-1 text-[10px] text-zinc-600 sm:flex">
              <Clock className="h-3 w-3" />
              Cập nhật: {state.lastUpdated}
            </span>
          )}
        </div>
        <ChevronDown className={`h-4 w-4 text-zinc-500 transition-transform ${expanded ? "rotate-180" : ""}`} />
      </button>

      {expanded && (
        <div className="space-y-3 border-t border-zinc-800 px-3 pb-4 pt-3 sm:px-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-end">
            <div className="w-full lg:flex-1">
              <label className="mb-1 block text-[11px] font-medium uppercase text-zinc-500">Danh sách</label>
              <div className="flex gap-2">
                <div className="flex flex-1 overflow-hidden rounded-md border border-zinc-700">
                  <button
                    onClick={() => setPreset("VN30")}
                    disabled={isBusy}
                    className={`flex-1 px-3 py-1.5 text-xs font-semibold transition-colors ${
                      preset === "VN30" ? "bg-emerald-600 text-white" : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
                    }`}
                  >
                    VN30
                  </button>
                  <button
                    onClick={() => setPreset("TOP100")}
                    disabled={isBusy}
                    className={`flex-1 px-3 py-1.5 text-xs font-semibold transition-colors ${
                      preset === "TOP100" ? "bg-amber-600 text-white" : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
                    }`}
                  >
                    Top 100
                  </button>
                </div>

                {isBusy ? (
                  <button
                    onClick={handleStop}
                    className="flex items-center justify-center gap-1.5 rounded-md bg-red-600/90 px-4 py-1.5 text-xs font-semibold text-white hover:bg-red-600"
                  >
                    <Square className="h-3.5 w-3.5" />
                    Stop
                  </button>
                ) : (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleLoad}
                      className="flex items-center justify-center gap-1.5 rounded-md bg-emerald-600 px-4 py-1.5 text-xs font-semibold text-white transition-all hover:bg-emerald-500"
                    >
                      <Download className="h-3.5 w-3.5" />
                      Load
                    </button>
                    <button
                      onClick={handleUpdate}
                      disabled={!canUpdate}
                      className={`flex items-center justify-center gap-1.5 rounded-md px-4 py-1.5 text-xs font-semibold transition-all ${
                        canUpdate
                          ? "bg-zinc-700 text-zinc-100 hover:bg-zinc-600"
                          : "cursor-not-allowed bg-zinc-800 text-zinc-500"
                      }`}
                    >
                      <RefreshCw className="h-3.5 w-3.5" />
                      Update
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="w-full">
            <div className="w-full lg:max-w-[540px]">
              <label className="mb-1 block text-[11px] font-medium uppercase text-zinc-500">Dữ liệu: {years} năm</label>
              <input
                type="range"
                min={1}
                max={10}
                value={years}
                onChange={(e) => setYears(Number(e.target.value))}
                disabled={isBusy}
                className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-zinc-700 accent-emerald-500 disabled:opacity-50"
              />
              <div className="mt-0.5 flex justify-between">
                <span className="text-[10px] text-zinc-600">1Y</span>
                <span className="text-[10px] text-zinc-600">5Y</span>
                <span className="text-[10px] text-zinc-600">10Y</span>
              </div>
            </div>
          </div>

          <div className="space-y-1">
            <div className="relative h-2 overflow-hidden rounded-full bg-zinc-800">
              <div
                className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-emerald-600 to-emerald-400 transition-all duration-300"
                style={{ width: `${Math.max(0, Math.min(100, state.percent))}%` }}
              />
              {isBusy && (
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent animate-[shimmer_1.5s_infinite]" />
              )}
            </div>
            <div className="flex items-center justify-between text-[11px]">
              <span className="pr-2 text-zinc-500">
                {state.currentSymbol && <span className="font-mono text-emerald-400">{state.currentSymbol}</span>}
                {state.currentSymbol && " — "}
                {state.message}
              </span>
              <span className="font-mono text-zinc-400">
                {state.loaded}/{state.total} ({Math.round(state.percent)}%)
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
