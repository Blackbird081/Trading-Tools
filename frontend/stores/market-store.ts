import { create } from "zustand";
import { subscribeWithSelector } from "zustand/middleware";
import type { TickData, CandleData } from "@/types/market";

interface MarketState {
  ticks: Record<string, TickData>;
  candles: Record<string, CandleData>;
  latestTick: TickData | null;

  updateTick: (tick: TickData) => void;
  updateCandle: (symbol: string, candle: CandleData) => void;
  bulkUpdateTicks: (ticks: TickData[]) => void;
}

export const useMarketStore = create<MarketState>()(
  subscribeWithSelector((set) => ({
    ticks: {},
    candles: {},
    latestTick: null,

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
  }))
);
