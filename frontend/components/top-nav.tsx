"use client";

import { useUIStore } from "@/stores/ui-store";
import { useMarketStore } from "@/stores/market-store";
import { Menu, Search } from "lucide-react";
import { cn } from "@/lib/utils";

export function TopNav() {
  const toggleSidebar = useUIStore((s) => s.toggleSidebar);
  const toggleCommandPalette = useUIStore((s) => s.toggleCommandPalette);
  const activeSymbol = useUIStore((s) => s.activeSymbol);
  const tick = useMarketStore((s) => s.ticks[activeSymbol]);
  const connectionStatus = useMarketStore((s) => s.connectionStatus);

  return (
    <header className="flex h-12 items-center justify-between border-b border-zinc-800 bg-zinc-950 px-3 md:px-4 shrink-0">
      <div className="flex items-center gap-2 md:gap-3">
        {/* Sidebar toggle — desktop only */}
        <button
          onClick={toggleSidebar}
          className="hidden md:flex rounded-md p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
        >
          <Menu className="h-4 w-4" />
        </button>

        {/* App name — mobile only */}
        <span className="md:hidden text-sm font-bold text-emerald-400">
          AlgoTrader
        </span>

        {/* Active symbol + price */}
        {activeSymbol && (
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-semibold text-emerald-400 hidden md:block">
              {activeSymbol}
            </span>
            {tick && (
              <>
                <span className="text-xs font-mono hidden md:block">
                  {tick.price.toFixed(2)}
                </span>
                <span
                  className={cn(
                    "text-[10px] hidden md:block",
                    tick.change > 0 ? "text-emerald-400" : tick.change < 0 ? "text-rose-400" : "text-zinc-500",
                  )}
                >
                  {tick.change > 0 ? "+" : ""}{tick.change.toFixed(2)} ({tick.changePct.toFixed(2)}%)
                </span>
              </>
            )}
          </div>
        )}
      </div>

      <div className="flex items-center gap-2">
        {/* Connection status dot — mobile */}
        <div className="flex items-center gap-1 md:hidden">
          <div className={cn(
            "w-1.5 h-1.5 rounded-full",
            connectionStatus === "connected" ? "bg-emerald-400" : "bg-zinc-600",
          )} />
          <span className="text-[10px] text-zinc-500">
            {connectionStatus === "connected" ? "LIVE" : "OFF"}
          </span>
        </div>

        {/* Search button */}
        <button
          onClick={toggleCommandPalette}
          className="flex items-center gap-1.5 rounded-md border border-zinc-800 px-2 md:px-3 py-1.5 text-xs text-zinc-500 hover:border-zinc-700 hover:text-zinc-300"
        >
          <Search className="h-3 w-3" />
          <span className="hidden md:block">Search...</span>
          <kbd className="hidden md:block rounded border border-zinc-700 bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-400">
            Ctrl+K
          </kbd>
        </button>
      </div>
    </header>
  );
}
