"use client";

import { useState } from "react";
import { useUIStore } from "@/stores/ui-store";

// ★ VN Market: lot size must be multiple of 100
const VN_LOT_SIZE = 100;

function validateLotSize(qty: string): string | null {
  const n = parseInt(qty, 10);
  if (isNaN(n) || n <= 0) return "Khối lượng phải là số dương";
  if (n % VN_LOT_SIZE !== 0) return `Khối lượng phải là bội số của ${VN_LOT_SIZE} (thị trường VN)`;
  return null;
}

export function OrderForm() {
  const activeSymbol = useUIStore((s) => s.activeSymbol);
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [quantityError, setQuantityError] = useState<string | null>(null);

  const handleQuantityChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setQuantity(val);
    // ★ Real-time lot size validation
    if (val) {
      setQuantityError(validateLotSize(val));
    } else {
      setQuantityError(null);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // ★ Final validation before submit
    const lotError = validateLotSize(quantity);
    if (lotError) {
      setQuantityError(lotError);
      return;
    }

    // Will be connected to OMS in production
    console.log("Order:", { symbol: activeSymbol, side, quantity: parseInt(quantity, 10), price });
  };

  const isValid = !quantityError && quantity !== "" && price !== "";

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
        <label className="text-xs text-zinc-500">
          Khối lượng{" "}
          <span className="text-zinc-600">(bội số {VN_LOT_SIZE})</span>
        </label>
        <input
          type="number"
          value={quantity}
          onChange={handleQuantityChange}
          placeholder="100"
          step={VN_LOT_SIZE}
          min={VN_LOT_SIZE}
          className={`w-full rounded border px-3 py-2 text-white ${
            quantityError
              ? "border-red-500 bg-zinc-800"
              : "border-zinc-700 bg-zinc-800"
          }`}
        />
        {/* ★ Inline error message */}
        {quantityError && (
          <p className="mt-1 text-xs text-red-400">{quantityError}</p>
        )}
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
        disabled={!isValid}
        className={`w-full rounded py-2.5 text-sm font-bold ${
          side === "BUY"
            ? "bg-green-600 hover:bg-green-700 disabled:bg-green-900"
            : "bg-red-600 hover:bg-red-700 disabled:bg-red-900"
        } text-white disabled:cursor-not-allowed disabled:opacity-50`}
      >
        {side === "BUY" ? "MUA" : "BÁN"} {activeSymbol}
      </button>
    </form>
  );
}
