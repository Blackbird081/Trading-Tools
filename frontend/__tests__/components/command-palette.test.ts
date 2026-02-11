import { describe, it, expect } from "vitest";
import { parseCommand } from "@/components/command-palette";

describe("parseCommand", () => {
  it("parses BUY command with price", () => {
    const result = parseCommand("BUY FPT 1000 PRICE 98.5");
    expect(result.action).toBe("BUY");
    expect(result.symbol).toBe("FPT");
    expect(result.quantity).toBe(1000);
    expect(result.price).toBe(98.5);
  });

  it("parses SELL command without price", () => {
    const result = parseCommand("SELL VNM 500");
    expect(result.action).toBe("SELL");
    expect(result.symbol).toBe("VNM");
    expect(result.quantity).toBe(500);
    expect(result.price).toBeUndefined();
  });

  it("parses BUY with @ syntax", () => {
    const result = parseCommand("buy hpg 200 @ 45.5");
    expect(result.action).toBe("BUY");
    expect(result.symbol).toBe("HPG");
    expect(result.quantity).toBe(200);
    expect(result.price).toBe(45.5);
  });

  it("returns UNKNOWN for invalid command", () => {
    const result = parseCommand("hello world");
    expect(result.action).toBe("UNKNOWN");
  });

  it("returns UNKNOWN for empty string", () => {
    const result = parseCommand("");
    expect(result.action).toBe("UNKNOWN");
  });
});
