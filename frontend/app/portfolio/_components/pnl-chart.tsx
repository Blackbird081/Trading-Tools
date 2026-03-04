"use client";

import { usePortfolioStore } from "@/stores/portfolio-store";

export function PnlChart() {
  const nav = usePortfolioStore((s) => s.nav);
  const cash = usePortfolioStore((s) => s.cash);
  const series = usePortfolioStore((s) => s.pnlSeries);

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
      <div className="mt-6 rounded border border-zinc-800 bg-zinc-950 p-3">
        <div className="mb-2 text-xs text-zinc-500">PnL 30 ngày gần nhất</div>
        {series.length === 0 ? (
          <div className="flex h-24 items-center justify-center text-xs text-zinc-600">Chưa có dữ liệu PnL.</div>
        ) : (
          <div className="space-y-1">
            {series.slice(-8).map((point) => (
              <div key={point.date} className="flex items-center justify-between text-xs">
                <span className="text-zinc-500">{point.date}</span>
                <span className={point.pnl >= 0 ? "text-emerald-400" : "text-red-400"}>
                  {point.pnl >= 0 ? "+" : ""}
                  {point.pnl.toLocaleString("vi-VN", { maximumFractionDigits: 0 })} ₫
                </span>
                <span className="text-zinc-400">
                  NAV {point.nav.toLocaleString("vi-VN", { maximumFractionDigits: 0 })}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
