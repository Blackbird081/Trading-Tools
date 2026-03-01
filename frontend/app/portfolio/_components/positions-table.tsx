"use client";

import { usePortfolioStore } from "@/stores/portfolio-store";

export function PositionsTable() {
  const positions = usePortfolioStore((s) => s.positions);

  if (positions.length === 0) {
    return (
      <div className="p-8 text-center text-zinc-500">
        Chưa có vị thế nào
      </div>
    );
  }

  return (
    <>
      <div className="space-y-2 md:hidden">
        {positions.map((pos) => {
          const pnl = (pos.marketPrice - pos.avgPrice) * pos.quantity;
          const pnlPct =
            pos.avgPrice > 0
              ? ((pos.marketPrice - pos.avgPrice) / pos.avgPrice) * 100
              : 0;
          return (
            <div key={pos.symbol} className="rounded-md border border-zinc-800 bg-zinc-950/60 p-3">
              <div className="flex items-center justify-between">
                <span className="text-base font-semibold text-amber-400">{pos.symbol}</span>
                <span className={pnl >= 0 ? "text-xs font-semibold text-green-400" : "text-xs font-semibold text-red-400"}>
                  {pnl >= 0 ? "+" : ""}
                  {pnl.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </span>
              </div>
              <div className="mt-2 grid grid-cols-2 gap-y-1 text-xs">
                <span className="text-zinc-500">Khối lượng</span>
                <span className="text-right text-zinc-200">{pos.quantity.toLocaleString()}</span>
                <span className="text-zinc-500">Giá TB</span>
                <span className="text-right text-zinc-200">{pos.avgPrice.toFixed(2)}</span>
                <span className="text-zinc-500">Giá TT</span>
                <span className="text-right text-zinc-200">{pos.marketPrice.toFixed(2)}</span>
                <span className="text-zinc-500">% Lãi/Lỗ</span>
                <span className={pnlPct >= 0 ? "text-right text-green-400" : "text-right text-red-400"}>
                  {pnlPct >= 0 ? "+" : ""}
                  {pnlPct.toFixed(2)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <div className="hidden overflow-x-auto md:block">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800 text-zinc-400">
              <th className="px-4 py-2 text-left">Mã CK</th>
              <th className="px-4 py-2 text-right">KL</th>
              <th className="px-4 py-2 text-right">Giá TB</th>
              <th className="px-4 py-2 text-right">Giá TT</th>
              <th className="px-4 py-2 text-right">Lãi/Lỗ</th>
              <th className="px-4 py-2 text-right">% Lãi/Lỗ</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((pos) => {
              const pnl = (pos.marketPrice - pos.avgPrice) * pos.quantity;
              const pnlPct =
                pos.avgPrice > 0
                  ? ((pos.marketPrice - pos.avgPrice) / pos.avgPrice) * 100
                  : 0;
              return (
                <tr
                  key={pos.symbol}
                  className="border-b border-zinc-800/50 hover:bg-zinc-800/30"
                >
                  <td className="px-4 py-2 font-semibold text-amber-400">
                    {pos.symbol}
                  </td>
                  <td className="px-4 py-2 text-right">
                    {pos.quantity.toLocaleString()}
                  </td>
                  <td className="px-4 py-2 text-right">
                    {pos.avgPrice.toFixed(2)}
                  </td>
                  <td className="px-4 py-2 text-right">
                    {pos.marketPrice.toFixed(2)}
                  </td>
                  <td
                    className={`px-4 py-2 text-right ${
                      pnl >= 0 ? "text-green-400" : "text-red-400"
                    }`}
                  >
                    {pnl >= 0 ? "+" : ""}
                    {pnl.toLocaleString(undefined, {
                      maximumFractionDigits: 0,
                    })}
                  </td>
                  <td
                    className={`px-4 py-2 text-right ${
                      pnlPct >= 0 ? "text-green-400" : "text-red-400"
                    }`}
                  >
                    {pnlPct >= 0 ? "+" : ""}
                    {pnlPct.toFixed(2)}%
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
