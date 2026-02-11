export default function PortfolioPage() {
  return (
    <div className="p-4">
      <h1 className="text-lg font-semibold mb-4">Portfolio</h1>
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <p className="text-xs text-zinc-500 uppercase">NAV</p>
          <p className="text-xl font-mono font-semibold text-zinc-100">0 ₫</p>
        </div>
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <p className="text-xs text-zinc-500 uppercase">Cash</p>
          <p className="text-xl font-mono font-semibold text-zinc-100">0 ₫</p>
        </div>
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <p className="text-xs text-zinc-500 uppercase">PnL</p>
          <p className="text-xl font-mono font-semibold text-emerald-400">+0 ₫</p>
        </div>
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <p className="text-xs text-zinc-500 uppercase">Purchasing Power</p>
          <p className="text-xl font-mono font-semibold text-zinc-100">0 ₫</p>
        </div>
      </div>
      <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <h2 className="text-sm font-medium text-zinc-400 mb-3">Positions</h2>
        <p className="text-sm text-zinc-500">No positions yet.</p>
      </div>
    </div>
  );
}
