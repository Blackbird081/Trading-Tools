"use client";

import { useEffect } from "react";
import { TradingErrorBoundary } from "@/components/error-boundary";
import { usePortfolioStore } from "@/stores/portfolio-store";
import { PositionsTable } from "./_components/positions-table";
import { PnlChart } from "./_components/pnl-chart";

function formatVnd(value: number): string {
  return `${value.toLocaleString("vi-VN", { maximumFractionDigits: 0 })} ₫`;
}

export default function PortfolioPage() {
  const {
    nav,
    cash,
    purchasingPower,
    realizedPnl,
    unrealizedPnl,
    lastSyncAt,
    loading,
    error,
    fetchPortfolio,
    fetchPnlSeries,
    refreshPortfolio,
  } = usePortfolioStore((s) => s);

  useEffect(() => {
    void fetchPortfolio();
    void fetchPnlSeries(30);
  }, [fetchPortfolio, fetchPnlSeries]);

  const totalPnl = realizedPnl + unrealizedPnl;

  return (
    <TradingErrorBoundary>
      <div className="p-3 sm:p-4">
        <div className="mb-4 flex items-center justify-between gap-3">
          <h1 className="text-xl font-semibold sm:text-2xl">Portfolio</h1>
          <button
            type="button"
            className="rounded border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-xs text-zinc-200 hover:bg-zinc-800"
            onClick={() => void refreshPortfolio()}
            disabled={loading}
          >
            {loading ? "Đang đồng bộ..." : "Refresh"}
          </button>
        </div>

        {error && <div className="mb-3 text-xs text-red-400">{error}</div>}
        <div className="mb-4 text-xs text-zinc-500">
          Last sync: {lastSyncAt ? new Date(lastSyncAt).toLocaleString("vi-VN") : "—"}
        </div>

        <div className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
            <p className="text-xs uppercase text-zinc-500">NAV</p>
            <p className="text-lg font-mono font-semibold text-zinc-100 sm:text-xl">{formatVnd(nav)}</p>
          </div>
          <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
            <p className="text-xs uppercase text-zinc-500">Cash</p>
            <p className="text-lg font-mono font-semibold text-zinc-100 sm:text-xl">{formatVnd(cash)}</p>
          </div>
          <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
            <p className="text-xs uppercase text-zinc-500">PnL</p>
            <p className={`text-lg font-mono font-semibold sm:text-xl ${totalPnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
              {totalPnl >= 0 ? "+" : ""}
              {formatVnd(totalPnl)}
            </p>
          </div>
          <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
            <p className="text-xs uppercase text-zinc-500">Purchasing Power</p>
            <p className="text-lg font-mono font-semibold text-zinc-100 sm:text-xl">{formatVnd(purchasingPower)}</p>
          </div>
        </div>
        <TradingErrorBoundary>
          <div className="mb-4 rounded-lg border border-zinc-800 bg-zinc-900 p-4">
            <h2 className="mb-3 text-sm font-medium text-zinc-400">Positions</h2>
            <PositionsTable />
          </div>
        </TradingErrorBoundary>
        <TradingErrorBoundary>
          <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
            <h2 className="mb-3 text-sm font-medium text-zinc-400">P&L Trend</h2>
            <PnlChart />
          </div>
        </TradingErrorBoundary>
      </div>
    </TradingErrorBoundary>
  );
}
