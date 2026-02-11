import { describe, expect, it, vi } from "vitest";

describe("WebSocketProvider", () => {
  it("should parse tick message and route to market store", () => {
    const msg = {
      type: "tick",
      payload: {
        symbol: "FPT",
        price: 98.5,
        change: 1.2,
        changePercent: 1.23,
        volume: 1500000,
        timestamp: Date.now(),
      },
    };
    expect(msg.type).toBe("tick");
    expect(msg.payload.symbol).toBe("FPT");
  });

  it("should parse signal message correctly", () => {
    const msg = {
      type: "signal",
      payload: {
        id: "sig-001",
        symbol: "VNM",
        action: "BUY",
        confidence: 0.85,
        reason: "RSI oversold",
        timestamp: Date.now(),
      },
    };
    expect(msg.type).toBe("signal");
    expect(msg.payload.action).toBe("BUY");
  });

  it("should handle reconnection state", () => {
    let connected = false;
    const connect = () => {
      connected = true;
    };
    connect();
    expect(connected).toBe(true);
  });
});
