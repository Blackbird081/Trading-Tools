import { describe, it, expect, beforeEach } from "vitest";
import { useMarketStore } from "@/stores/market-store";

describe("MarketStore", () => {
  beforeEach(() => {
    useMarketStore.setState({
      ticks: {},
      candles: {},
      latestTick: null,
    });
  });

  it("updates single tick by symbol", () => {
    const tick = {
      symbol: "FPT",
      price: 98.5,
      change: 1.2,
      changePct: 1.23,
      volume: 50000,
      high: 99.0,
      low: 97.0,
      open: 97.3,
      ceiling: 104.0,
      floor: 91.0,
      reference: 97.3,
      timestamp: Date.now(),
    };

    useMarketStore.getState().updateTick(tick);

    const state = useMarketStore.getState();
    expect(state.ticks["FPT"]).toEqual(tick);
    expect(state.latestTick).toEqual(tick);
  });

  it("bulk update overwrites existing ticks", () => {
    const ticks = [
      {
        symbol: "FPT",
        price: 98.5,
        change: 1.2,
        changePct: 1.23,
        volume: 50000,
        high: 99.0,
        low: 97.0,
        open: 97.3,
        ceiling: 104.0,
        floor: 91.0,
        reference: 97.3,
        timestamp: 1,
      },
      {
        symbol: "VNM",
        price: 72.0,
        change: -0.5,
        changePct: -0.69,
        volume: 30000,
        high: 73.0,
        low: 71.0,
        open: 72.5,
        ceiling: 77.0,
        floor: 67.0,
        reference: 72.5,
        timestamp: 2,
      },
      {
        symbol: "FPT",
        price: 99.0,
        change: 1.7,
        changePct: 1.74,
        volume: 60000,
        high: 99.5,
        low: 97.0,
        open: 97.3,
        ceiling: 104.0,
        floor: 91.0,
        reference: 97.3,
        timestamp: 3,
      },
    ];

    useMarketStore.getState().bulkUpdateTicks(ticks);

    const state = useMarketStore.getState();
    expect(state.ticks["FPT"]?.price).toBe(99.0);
    expect(state.ticks["VNM"]?.price).toBe(72.0);
    expect(state.latestTick?.symbol).toBe("FPT");
  });

  it("does not mutate previous state reference", () => {
    const before = useMarketStore.getState().ticks;

    useMarketStore.getState().updateTick({
      symbol: "MWG",
      price: 45.2,
      change: 0.8,
      changePct: 1.8,
      volume: 20000,
      high: 46.0,
      low: 44.0,
      open: 44.4,
      ceiling: 48.0,
      floor: 41.0,
      reference: 44.4,
      timestamp: Date.now(),
    });

    const after = useMarketStore.getState().ticks;
    expect(before).not.toBe(after);
  });

  it("updateCandle stores candle by symbol", () => {
    const candle = {
      time: 1707580800,
      open: 97.3,
      high: 99.0,
      low: 96.5,
      close: 98.5,
    };

    useMarketStore.getState().updateCandle("FPT", candle);

    expect(useMarketStore.getState().candles["FPT"]).toEqual(candle);
  });
});
