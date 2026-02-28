import { create } from "zustand";
import { subscribeWithSelector } from "zustand/middleware";
import type { TickData, CandleData } from "@/types/market";

type ConnectionStatus = "connected" | "disconnected" | "connecting";

interface MarketState {
  ticks: Record<string, TickData>;
  candles: Record<string, CandleData>;
  latestTick: TickData | null;
  connectionStatus: ConnectionStatus;  // ★ NEW: WebSocket connection status

  updateTick: (tick: TickData) => void;
  updateCandle: (symbol: string, candle: CandleData) => void;
  bulkUpdateTicks: (ticks: TickData[]) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;  // ★ NEW
}

export const useMarketStore = create<MarketState>()(
  subscribeWithSelector((set) => ({
    ticks: {},
    candles: {},
    latestTick: null,
    connectionStatus: "disconnected",

    updateTick: (tick) =>
      set((state) => ({
        latestTick: tick,
        ticks: { ...state.ticks, [tick.symbol]: tick },
      })),

    updateCandle: (symbol, candle) =>
      set((state) => ({
        candles: { ...state.candles, [symbol]: candle },
      })),

    bulkUpdateTicks: (ticks) =>
      set((state) => {
        const updated = { ...state.ticks };
        for (const tick of ticks) {
          updated[tick.symbol] = tick;
        }
        return {
          ticks: updated,
          latestTick: ticks[ticks.length - 1] ?? null,
        };
      }),

    setConnectionStatus: (status) => set({ connectionStatus: status }),
  }))
);
