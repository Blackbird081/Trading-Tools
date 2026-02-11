"use client";

import { useState } from "react";
import { useUIStore } from "@/stores/ui-store";

export function OrderForm() {
  const activeSymbol = useUIStore((s) => s.activeSymbol);
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Will be connected to OMS in production
    console.log("Order:", { symbol: activeSymbol, side, quantity, price });
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4 rounded-lg border border-zinc-800 bg-zinc-900 p-6"
    >
      <h3 className="text-sm font-medium text-zinc-400">Đặt lệnh</h3>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => setSide("BUY")}
          className={`flex-1 rounded px-4 py-2 text-sm font-semibold ${
            side === "BUY"
              ? "bg-green-600 text-white"
              : "bg-zinc-800 text-zinc-400"
          }`}
        >
          MUA
        </button>
        <button
          type="button"
          onClick={() => setSide("SELL")}
          className={`flex-1 rounded px-4 py-2 text-sm font-semibold ${
            side === "SELL"
              ? "bg-red-600 text-white"
              : "bg-zinc-800 text-zinc-400"
          }`}
        >
          BÁN
        </button>
      </div>

      <div>
        <label className="text-xs text-zinc-500">Mã CK</label>
        <input
          type="text"
          value={activeSymbol}
          readOnly
          className="w-full rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-white"
        />
      </div>

      <div>
        <label className="text-xs text-zinc-500">Khối lượng</label>
        <input
          type="number"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          placeholder="100"
          step="100"
          className="w-full rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-white"
        />
      </div>

      <div>
        <label className="text-xs text-zinc-500">Giá</label>
        <input
          type="number"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
          placeholder="0.00"
          step="0.1"
          className="w-full rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-white"
        />
      </div>

      <button
        type="submit"
        className={`w-full rounded py-2.5 text-sm font-bold ${
          side === "BUY"
            ? "bg-green-600 hover:bg-green-700"
            : "bg-red-600 hover:bg-red-700"
        } text-white`}
      >
        {side === "BUY" ? "MUA" : "BÁN"} {activeSymbol}
      </button>
    </form>
  );
}
