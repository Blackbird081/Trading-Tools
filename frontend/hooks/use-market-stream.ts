"use client";

import { useEffect, useRef } from "react";
import type { GridApi } from "ag-grid-community";
import { useMarketStore } from "@/stores/market-store";
import type { TickData } from "@/types/market";

export function useMarketStream(gridApi: GridApi | null) {
  const pendingUpdates = useRef<Map<string, TickData>>(new Map());
  const rafId = useRef<number | null>(null);

  useEffect(() => {
    if (!gridApi) return;

    const unsubscribe = useMarketStore.subscribe(
      (state) => state.latestTick,
      (tick) => {
        if (!tick) return;
        pendingUpdates.current.set(tick.symbol, tick);
      }
    );

    function flushUpdates() {
      const updates = pendingUpdates.current;
      if (updates.size > 0 && gridApi) {
        gridApi.applyTransactionAsync({
          update: Array.from(updates.values()),
        });
        updates.clear();
      }
      rafId.current = requestAnimationFrame(flushUpdates);
    }

    rafId.current = requestAnimationFrame(flushUpdates);

    return () => {
      unsubscribe();
      if (rafId.current !== null) {
        cancelAnimationFrame(rafId.current);
        rafId.current = null;
      }
    };
  }, [gridApi]);
}
