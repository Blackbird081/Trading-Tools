import { describe, it, expect, beforeEach } from "vitest";
import { useSignalStore } from "@/stores/signal-store";

describe("SignalStore", () => {
  beforeEach(() => {
    useSignalStore.setState({ signals: [], latestSignal: null });
  });

  it("adds a signal", () => {
    const signal = {
      id: "sig-1",
      symbol: "FPT",
      action: "BUY" as const,
      score: 7.5,
      reason: "Golden cross + oversold RSI",
      timestamp: Date.now(),
    };

    useSignalStore.getState().addSignal(signal);

    const state = useSignalStore.getState();
    expect(state.signals).toHaveLength(1);
    expect(state.latestSignal).toEqual(signal);
  });

  it("caps signals at 100", () => {
    for (let i = 0; i < 110; i++) {
      useSignalStore.getState().addSignal({
        id: `sig-${i}`,
        symbol: "FPT",
        action: "BUY",
        score: 5.0,
        reason: "Test",
        timestamp: i,
      });
    }

    expect(useSignalStore.getState().signals).toHaveLength(100);
  });

  it("clears signals", () => {
    useSignalStore.getState().addSignal({
      id: "sig-1",
      symbol: "FPT",
      action: "SELL",
      score: -6.0,
      reason: "Death cross",
      timestamp: Date.now(),
    });

    useSignalStore.getState().clearSignals();

    const state = useSignalStore.getState();
    expect(state.signals).toHaveLength(0);
    expect(state.latestSignal).toBeNull();
  });
});
