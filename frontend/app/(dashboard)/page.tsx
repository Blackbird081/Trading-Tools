"use client";

import { Suspense } from "react";
import { PriceBoard } from "./_components/price-board";
import { DataLoader } from "./_components/data-loader";
import { MarketIndexBar } from "@/components/market-index-bar";
import { TradingErrorBoundary } from "@/components/error-boundary";
import { useSignalStore } from "@/stores/signal-store";
import type { AgentSignal } from "@/types/market";

function LoadingSkeleton() {
  return (
    <div className="flex items-center justify-center h-full bg-zinc-950">
      <div className="h-5 w-5 animate-spin rounded-full border-2 border-zinc-700 border-t-emerald-400" />
    </div>
  );
}

function actionClass(action: AgentSignal["action"]): string {
  if (action === "BUY") return "text-emerald-400";
  if (action === "SELL") return "text-rose-400";
  return "text-zinc-400";
}

function formatSignalTime(timestamp: number): string {
  const ms = timestamp < 1_000_000_000_000 ? timestamp * 1000 : timestamp;
  return new Date(ms).toLocaleTimeString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function DashboardPage() {
  const signals = useSignalStore((s) => s.signals);
  const latestSignal = signals[0] ?? null;
  const hasSignals = signals.length > 0;
  const recentSignals = signals.slice(0, 8);

  return (
    <div className="flex h-full flex-col">
      {/* ── Market Index Bar (VN-Index, HNX-Index, UPCOM) ── */}
      <MarketIndexBar />

      {/* ── Data loader bar ── */}
      <DataLoader />

      {/* ── Main content: Price Board chiếm toàn bộ không gian ── */}
      <div className="flex flex-1 min-h-0 flex-col gap-2 p-2 lg:flex-row lg:gap-0.5 lg:p-0.5">
        {/* Price Board — full width */}
        <div className="min-h-[360px] flex-1 overflow-hidden rounded-sm border border-zinc-800/50 lg:min-h-0">
          <TradingErrorBoundary>
            <Suspense fallback={<LoadingSkeleton />}>
              <PriceBoard />
            </Suspense>
          </TradingErrorBoundary>
        </div>

        {/* Agent Signals panel — desktop only, render when real signals exist */}
        {hasSignals && (
          <TradingErrorBoundary>
            <aside className="hidden w-80 shrink-0 flex-col gap-3 overflow-auto rounded-sm border border-zinc-800/50 bg-zinc-900/80 p-3 lg:flex">
              <header className="border-b border-zinc-800/60 pb-2">
                <div className="mb-1 flex items-center gap-2">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-200">Agent Signals</h3>
                  <span className="text-xs text-zinc-500">- AI analysis</span>
                </div>
                <p className="text-[11px] text-zinc-500">{signals.length} tín hiệu gần nhất từ pipeline</p>
              </header>

              {latestSignal && (
                <section className="rounded border border-zinc-800/70 bg-zinc-950/70 p-2.5">
                  <div className="mb-1 flex items-center justify-between">
                    <span className="font-semibold text-zinc-100">{latestSignal.symbol}</span>
                    <span className={`text-xs font-semibold ${actionClass(latestSignal.action)}`}>
                      {latestSignal.action}
                    </span>
                  </div>
                  <div className="mb-1 flex items-center justify-between text-xs text-zinc-500">
                    <span>Score: {latestSignal.score.toFixed(2)}</span>
                    <span>{formatSignalTime(latestSignal.timestamp)}</span>
                  </div>
                  <p className="max-h-14 overflow-hidden text-xs leading-relaxed text-zinc-400">{latestSignal.reason}</p>
                </section>
              )}

              <div className="flex min-h-0 flex-1 flex-col gap-1.5">
                {recentSignals.map((signal) => (
                  <div
                    key={signal.id}
                    className="flex items-center justify-between rounded border border-zinc-800/50 px-2 py-1.5 text-xs"
                  >
                    <div className="min-w-0">
                      <p className="font-medium text-zinc-200">{signal.symbol}</p>
                      <p className="truncate text-[11px] text-zinc-500">{signal.reason}</p>
                    </div>
                    <div className="ml-2 shrink-0 text-right">
                      <p className={`font-semibold ${actionClass(signal.action)}`}>{signal.action}</p>
                      <p className="text-[11px] text-zinc-500">{formatSignalTime(signal.timestamp)}</p>
                    </div>
                  </div>
                ))}
              </div>
            </aside>
          </TradingErrorBoundary>
        )}

        {/* Mobile helper card */}
        <div className="rounded-sm border border-zinc-800/50 bg-zinc-900/60 p-2 lg:hidden">
          <p className="text-xs leading-relaxed text-zinc-500">
            Nhấn vào mã cổ phiếu để mở biểu đồ kỹ thuật và tín hiệu AI chi tiết.
          </p>
        </div>
      </div>
    </div>
  );
}
