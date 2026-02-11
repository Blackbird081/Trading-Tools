"use client";

import { usePortfolioStore } from "@/stores/portfolio-store";

export function PnlChart() {
  const nav = usePortfolioStore((s) => s.nav);
  const cash = usePortfolioStore((s) => s.cash);

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-6">
      <h3 className="mb-4 text-sm font-medium text-zinc-400">
        Tổng quan tài sản
      </h3>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-xs text-zinc-500">NAV</p>
          <p className="text-xl font-bold text-white">
            {nav.toLocaleString(undefined, {
              maximumFractionDigits: 0,
            })}
          </p>
        </div>
        <div>
          <p className="text-xs text-zinc-500">Tiền mặt</p>
          <p className="text-xl font-bold text-emerald-400">
            {cash.toLocaleString(undefined, {
              maximumFractionDigits: 0,
            })}
          </p>
        </div>
      </div>
      <div className="mt-6 flex h-32 items-center justify-center rounded border border-dashed border-zinc-700 text-zinc-500">
        Chart placeholder — sẽ dùng Lightweight Charts
      </div>
    </div>
  );
}
