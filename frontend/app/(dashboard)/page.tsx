"use client";

import { Suspense } from "react";
import { PriceBoard } from "./_components/price-board";
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

        {/* Agent Signals panel — desktop sidebar */}
        <TradingErrorBoundary>
          <div className="hidden w-72 shrink-0 flex-col gap-3 overflow-auto rounded-sm border border-zinc-800/50 bg-zinc-900/80 p-3 lg:flex">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <h3 className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">
                  Agent Signals
                </h3>
                <span className="text-xs text-zinc-600">— AI analysis</span>
              </div>
              <p className="text-zinc-600 text-xs">Đang chờ tín hiệu từ pipeline...</p>
            </div>

            {/* Hướng dẫn click-to-chart */}
            <div className="mt-auto pt-3 border-t border-zinc-800/60">
              <p className="text-[11px] text-zinc-500 leading-relaxed">
                💡 <span className="text-zinc-400">Click vào mã cổ phiếu</span> để xem biểu đồ kỹ thuật chi tiết.
              </p>
            </div>
          </div>
        </TradingErrorBoundary>

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
