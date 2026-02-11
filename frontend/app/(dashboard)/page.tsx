"use client";

import { Suspense } from "react";
import { PriceBoard } from "./_components/price-board";
import { TradingChart } from "./_components/trading-chart";
import { DataLoader } from "./_components/data-loader";

function ChartSkeleton() {
  return (
    <div className="flex items-center justify-center bg-zinc-950">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-700 border-t-emerald-400" />
    </div>
  );
}

function GridSkeleton() {
  return (
    <div className="flex items-center justify-center bg-zinc-950">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-700 border-t-emerald-400" />
    </div>
  );
}

export default function DashboardPage() {
  return (
    <div className="flex h-full flex-col gap-1 p-1">
      {/* Data loader bar */}
      <DataLoader />

      {/* Main content */}
      <div className="grid flex-1 grid-cols-[1fr_400px] grid-rows-[60%_40%] gap-1 min-h-0">
        <Suspense fallback={<ChartSkeleton />}>
          <TradingChart />
        </Suspense>

        <div className="row-span-2">
          <Suspense fallback={<GridSkeleton />}>
            <PriceBoard />
          </Suspense>
        </div>

        <div className="bg-zinc-900 rounded-md p-3">
          <h3 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-2">
            Agent Signals
          </h3>
          <p className="text-zinc-500 text-sm">Waiting for signals...</p>
        </div>
      </div>
    </div>
  );
}
