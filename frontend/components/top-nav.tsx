"use client";

import { useUIStore } from "@/stores/ui-store";
import { useMarketStore } from "@/stores/market-store";
import { Menu, Search } from "lucide-react";

export function TopNav() {
  const toggleSidebar = useUIStore((s) => s.toggleSidebar);
  const toggleCommandPalette = useUIStore((s) => s.toggleCommandPalette);
  const activeSymbol = useUIStore((s) => s.activeSymbol);
  const tick = useMarketStore((s) => s.ticks[activeSymbol]);

  return (
    <header className="flex h-12 items-center justify-between border-b border-zinc-800 bg-zinc-950 px-4">
      <div className="flex items-center gap-3">
        <button
          onClick={toggleSidebar}
          className="rounded-md p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
        >
          <Menu className="h-4 w-4" />
        </button>

        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-emerald-400">
            {activeSymbol}
          </span>
          {tick && (
            <>
              <span className="text-sm font-mono">
                {tick.price.toFixed(2)}
              </span>
              <span
                className={
                  tick.change > 0
                    ? "text-xs text-emerald-400"
                    : tick.change < 0
                      ? "text-xs text-rose-400"
                      : "text-xs text-zinc-500"
                }
              >
                {tick.change > 0 ? "+" : ""}
                {tick.change.toFixed(2)} ({tick.changePct.toFixed(2)}%)
              </span>
            </>
          )}
        </div>
      </div>

      <button
        onClick={toggleCommandPalette}
        className="flex items-center gap-2 rounded-md border border-zinc-800 px-3 py-1.5 text-xs text-zinc-500 hover:border-zinc-700 hover:text-zinc-300"
      >
        <Search className="h-3 w-3" />
        <span>Search...</span>
        <kbd className="rounded border border-zinc-700 bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-400">
          Ctrl+K
        </kbd>
      </button>
    </header>
  );
}
