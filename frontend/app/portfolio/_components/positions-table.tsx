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
    <div className="overflow-x-auto">
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
  );
}
