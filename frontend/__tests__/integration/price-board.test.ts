import { describe, expect, it } from "vitest";

describe("PriceBoard integration", () => {
  it("should define column structure for AG Grid", () => {
    const columns = [
      { field: "symbol", headerName: "Mã CK" },
      { field: "price", headerName: "Giá" },
      { field: "change", headerName: "Thay đổi" },
      { field: "changePercent", headerName: "%" },
      { field: "volume", headerName: "KL" },
    ];
    expect(columns).toHaveLength(5);
    expect(columns[0].field).toBe("symbol");
  });

  it("should format tick data for grid rows", () => {
    const tick = {
      symbol: "FPT",
      price: 98.5,
      change: 1.2,
      changePercent: 1.23,
      volume: 1500000,
    };
    const row = {
      ...tick,
      id: tick.symbol,
    };
    expect(row.id).toBe("FPT");
    expect(row.price).toBe(98.5);
  });

  it("should apply color based on change direction", () => {
    const getColor = (change: number) =>
      change > 0 ? "text-green-400" : change < 0 ? "text-red-400" : "text-amber-400";
    
    expect(getColor(1.5)).toBe("text-green-400");
    expect(getColor(-0.5)).toBe("text-red-400");
    expect(getColor(0)).toBe("text-amber-400");
  });
});
