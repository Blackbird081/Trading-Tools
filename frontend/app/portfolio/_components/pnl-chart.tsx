"use client";

import { usePortfolioStore } from "@/stores/portfolio-store";

export function PnlChart() {
  const nav = usePortfolioStore((s) => s.nav);
  const cash = usePortfolioStore((s) => s.cash);

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4 sm:p-6">
      <h3 className="mb-4 text-sm font-medium text-zinc-400">
        Tổng quan tài sản
      </h3>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <p className="text-xs text-zinc-500">NAV</p>
          <p className="text-lg font-bold text-white sm:text-xl">
            {nav.toLocaleString(undefined, {
              maximumFractionDigits: 0,
            })}
          </p>
        </div>
        <div>
          <p className="text-xs text-zinc-500">Tiền mặt</p>
          <p className="text-lg font-bold text-emerald-400 sm:text-xl">
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
