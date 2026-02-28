"use client";

import { Suspense } from "react";
import { PriceBoard } from "./_components/price-board";
import { TradingChart } from "./_components/trading-chart";
import { DataLoader } from "./_components/data-loader";
import { MarketIndexBar } from "@/components/market-index-bar";
import { TradingErrorBoundary } from "@/components/error-boundary";

function LoadingSkeleton() {
  return (
    <div className="flex items-center justify-center h-full bg-zinc-950">
      <div className="h-5 w-5 animate-spin rounded-full border-2 border-zinc-700 border-t-emerald-400" />
    </div>
  );
}

export default function DashboardPage() {
  return (
    <div className="flex h-full flex-col">
      {/* ── Market Index Bar (VN-Index, HNX-Index, UPCOM) ── */}
      <MarketIndexBar />

      {/* ── Data loader bar ── */}
      <DataLoader />

      {/* ── Main content ── */}
      <div className="grid flex-1 grid-cols-[1fr_380px] grid-rows-[60%_40%] gap-0.5 min-h-0 p-0.5">
        {/* Chart */}
        <TradingErrorBoundary>
          <Suspense fallback={<LoadingSkeleton />}>
            <TradingChart />
          </Suspense>
        </TradingErrorBoundary>

        {/* Price Board — spans 2 rows */}
        <div className="row-span-2 border border-zinc-800/50 rounded-sm overflow-hidden">
          <TradingErrorBoundary>
            <Suspense fallback={<LoadingSkeleton />}>
              <PriceBoard />
            </Suspense>
          </TradingErrorBoundary>
        </div>

        {/* Agent Signals panel */}
        <TradingErrorBoundary>
          <div className="bg-zinc-900/80 border border-zinc-800/50 rounded-sm p-3 overflow-auto">
            <div className="flex items-center gap-2 mb-2">
              <h3 className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">
                Agent Signals
              </h3>
              <span className="text-xs text-zinc-600">— Real-time AI analysis</span>
            </div>
            <p className="text-zinc-600 text-xs">Đang chờ tín hiệu từ pipeline...</p>
          </div>
        </TradingErrorBoundary>
      </div>
    </div>
  );
}
