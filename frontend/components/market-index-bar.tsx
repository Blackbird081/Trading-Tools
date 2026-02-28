"use client";

/**
 * Market Index Bar — hiển thị VN-Index, HNX-Index, UPCOM-Index.
 * ★ Inspired by sieucophieu.vn/bang-dien top bar.
 * ★ Real-time updates via Zustand market store.
 */

import { useState, useEffect } from "react";
import { useMarketStore } from "@/stores/market-store";
import { cn } from "@/lib/utils";

interface IndexData {
  name: string;
  value: number;
  change: number;
  changePct: number;
  volume?: number;
}

// Mock data — sẽ được thay bằng real data từ WebSocket
const MOCK_INDICES: IndexData[] = [
  { name: "VN-Index", value: 1285.42, change: +8.35, changePct: +0.65, volume: 512_000_000 },
  { name: "HNX-Index", value: 228.15, change: -1.22, changePct: -0.53, volume: 85_000_000 },
  { name: "UPCOM", value: 95.67, change: +0.43, changePct: +0.45, volume: 42_000_000 },
  { name: "VN30", value: 1312.80, change: +9.10, changePct: +0.70 },
];

function IndexItem({ index }: { index: IndexData }) {
  const isUp = index.change > 0;
  const isDown = index.change < 0;

  return (
    <div className="market-index-item flex items-center gap-3 py-2">
      <span className="text-xs font-semibold text-zinc-300 min-w-[80px]">
        {index.name}
      </span>
      <span
        className={cn(
          "font-mono text-sm font-bold tabular-nums",
          isUp && "text-emerald-400",
          isDown && "text-rose-400",
          !isUp && !isDown && "text-amber-400",
        )}
      >
        {index.value.toLocaleString("vi-VN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
      </span>
      <span
        className={cn(
          "font-mono text-xs tabular-nums",
          isUp && "text-emerald-400",
          isDown && "text-rose-400",
          !isUp && !isDown && "text-zinc-500",
        )}
      >
        {isUp ? "▲" : isDown ? "▼" : "—"}
        {" "}
        {Math.abs(index.change).toFixed(2)}
        {" "}
        ({isUp ? "+" : ""}{index.changePct.toFixed(2)}%)
      </span>
      {index.volume && (
        <span className="text-xs text-zinc-600 hidden xl:block">
          KL: {(index.volume / 1_000_000).toFixed(0)}M
        </span>
      )}
    </div>
  );
}

export function MarketIndexBar() {
  const connectionStatus = useMarketStore((s) => s.connectionStatus);
  const [time, setTime] = useState<string>("");

  useEffect(() => {
    setTime(new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
    const interval = setInterval(() => {
      setTime(new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="market-index-bar flex items-center justify-between px-2 h-10 shrink-0">
      {/* Left: Market indices */}
      <div className="flex items-center overflow-x-auto">
        {MOCK_INDICES.map((index) => (
          <IndexItem key={index.name} index={index} />
        ))}
      </div>

      {/* Right: Connection status + time */}
      <div className="flex items-center gap-3 px-4 shrink-0">
        <div className="flex items-center gap-1.5">
          <div
            className={cn(
              "w-1.5 h-1.5 rounded-full",
              connectionStatus === "connected" ? "bg-emerald-400 live-dot" : "bg-zinc-600",
            )}
          />
          <span className="text-xs text-zinc-500">
            {connectionStatus === "connected" ? "LIVE" : "OFFLINE"}
          </span>
        </div>
        <span className="text-xs text-zinc-600 font-mono">
          {time}
        </span>
      </div>
    </div>
  );
}
