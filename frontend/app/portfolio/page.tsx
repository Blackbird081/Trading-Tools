import { TradingErrorBoundary } from "@/components/error-boundary";
import { PositionsTable } from "./_components/positions-table";
import { PnlChart } from "./_components/pnl-chart";

export default function PortfolioPage() {
  return (
    <TradingErrorBoundary>
      <div className="p-3 sm:p-4">
        <h1 className="mb-4 text-xl font-semibold sm:text-2xl">Portfolio</h1>
        <div className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
            <p className="text-xs text-zinc-500 uppercase">NAV</p>
            <p className="text-lg font-mono font-semibold text-zinc-100 sm:text-xl">0 ₫</p>
          </div>
          <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
            <p className="text-xs text-zinc-500 uppercase">Cash</p>
            <p className="text-lg font-mono font-semibold text-zinc-100 sm:text-xl">0 ₫</p>
          </div>
          <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
            <p className="text-xs text-zinc-500 uppercase">PnL</p>
            <p className="text-lg font-mono font-semibold text-emerald-400 sm:text-xl">+0 ₫</p>
          </div>
          <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
            <p className="text-xs text-zinc-500 uppercase">Purchasing Power</p>
            <p className="text-lg font-mono font-semibold text-zinc-100 sm:text-xl">0 ₫</p>
          </div>
        </div>
        <TradingErrorBoundary>
          <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4 mb-4">
            <h2 className="text-sm font-medium text-zinc-400 mb-3">Positions</h2>
            <PositionsTable />
          </div>
        </TradingErrorBoundary>
        <TradingErrorBoundary>
          <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
            <h2 className="text-sm font-medium text-zinc-400 mb-3">P&L Chart</h2>
            <PnlChart />
          </div>
        </TradingErrorBoundary>
      </div>
    </TradingErrorBoundary>
  );
}
