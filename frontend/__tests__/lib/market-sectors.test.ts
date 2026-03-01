import { describe, expect, it } from "vitest";
import { buildMarketSectors, TOP100_SYMBOLS, VN30_SYMBOLS } from "@/lib/market-sectors";
import type { TickData } from "@/types/market";

function makeTick(symbol: string): TickData {
  return {
    symbol,
    price: 10,
    change: 0,
    changePct: 0,
    volume: 1000,
    high: 10.5,
    low: 9.5,
    open: 10,
    ceiling: 11,
    floor: 9,
    reference: 10,
    timestamp: Date.now(),
  };
}

describe("buildMarketSectors", () => {
  it("returns VN30 sector for VN30 preset", () => {
    const sectors = buildMarketSectors("VN30", {} as Record<string, TickData>);
    expect(sectors).toHaveLength(1);
    expect(sectors[0]?.title).toBe("VN30");
    expect(sectors[0]?.symbols).toHaveLength(VN30_SYMBOLS.length);
  });

  it("returns many sectors for TOP100 preset", () => {
    const sectors = buildMarketSectors("TOP100", {} as Record<string, TickData>);
    expect(sectors.length).toBeGreaterThan(6);
    expect(sectors[0]?.title).toBe("VN30");
  });

  it("uses active ticks subset when market data is available", () => {
    const ticks: Record<string, TickData> = {
      FPT: makeTick("FPT"),
      DIG: makeTick("DIG"),
      BSI: makeTick("BSI"),
      PVD: makeTick("PVD"),
    };

    const sectors = buildMarketSectors("TOP100", ticks);
    const allSymbols = sectors.flatMap((sector) => sector.symbols);
    expect(allSymbols).toEqual(["FPT", "DIG", "BSI", "PVD"]);
  });

  it("keeps VN30 symbols grouped first under TOP100", () => {
    const ticks: Record<string, TickData> = {
      ACB: makeTick("ACB"),
      DIG: makeTick("DIG"),
      VND: makeTick("VND"),
    };

    const sectors = buildMarketSectors("TOP100", ticks);
    expect(sectors[0]?.title).toBe("VN30");
    expect(sectors[0]?.symbols).toEqual(["ACB"]);
  });

  it("keeps symbol universe aligned with TOP100 list", () => {
    const sectors = buildMarketSectors("TOP100", {} as Record<string, TickData>);
    const allSymbols = new Set(sectors.flatMap((sector) => sector.symbols));
    for (const symbol of allSymbols) {
      expect(TOP100_SYMBOLS.includes(symbol)).toBe(true);
    }
  });
});
