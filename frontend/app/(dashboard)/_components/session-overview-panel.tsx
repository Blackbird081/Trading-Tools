"use client";

import { useMemo } from "react";
import { useMarketStore } from "@/stores/market-store";
import { cn } from "@/lib/utils";

function formatCompact(value: number): string {
  return new Intl.NumberFormat("vi-VN", {
    notation: "compact",
    compactDisplay: "short",
    maximumFractionDigits: 1,
  }).format(value);
}

function formatPct(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

function formatTime(ts: number | null): string {
  if (!ts) return "—";
  const ms = ts < 1_000_000_000_000 ? ts * 1000 : ts;
  return new Date(ms).toLocaleTimeString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function statClass(value: number): string {
  if (value > 0) return "text-emerald-400";
  if (value < 0) return "text-rose-400";
  return "text-zinc-300";
}

function SummaryRow({ label, value, valueClass }: { label: string; value: string; valueClass?: string }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-zinc-800/40 py-1.5 text-xs">
      <span className="text-zinc-500">{label}</span>
      <span className={cn("font-mono font-medium text-zinc-200", valueClass)}>{value}</span>
    </div>
  );
}

export function SessionOverviewPanel() {
  const ticks = useMarketStore((s) => s.ticks);
  const connectionStatus = useMarketStore((s) => s.connectionStatus);
  const connectionLabel =
    connectionStatus === "connected"
      ? "Live"
      : connectionStatus === "connecting"
        ? "Đang kết nối"
        : "Offline";

  const stats = useMemo(() => {
    const rows = Object.values(ticks);
    const total = rows.length;
    if (total === 0) {
      return {
        total: 0,
        up: 0,
        down: 0,
        flat: 0,
        volume: 0,
        tradedValue: 0,
        avgChangePct: 0,
        avgRangePct: 0,
        topGain: null as null | { symbol: string; changePct: number },
        topLoss: null as null | { symbol: string; changePct: number },
        topVolume: null as null | { symbol: string; volume: number },
        latestTs: null as number | null,
      };
    }

    let up = 0;
    let down = 0;
    let flat = 0;
    let volume = 0;
    let tradedValue = 0;
    let changePctSum = 0;
    let rangePctSum = 0;
    let latestTs = 0;

    const first = rows[0]!;
    let topGain = { symbol: first.symbol, changePct: first.changePct };
    let topLoss = { symbol: first.symbol, changePct: first.changePct };
    let topVolume = { symbol: first.symbol, volume: first.volume };

    for (const t of rows) {
      if (t.change > 0) up += 1;
      else if (t.change < 0) down += 1;
      else flat += 1;

      volume += t.volume;
      tradedValue += t.volume * t.price;
      changePctSum += t.changePct;
      if (t.reference > 0) {
        rangePctSum += ((t.high - t.low) / t.reference) * 100;
      }
      if (t.timestamp > latestTs) latestTs = t.timestamp;

      if (t.changePct > topGain.changePct) {
        topGain = { symbol: t.symbol, changePct: t.changePct };
      }
      if (t.changePct < topLoss.changePct) {
        topLoss = { symbol: t.symbol, changePct: t.changePct };
      }
      if (t.volume > topVolume.volume) {
        topVolume = { symbol: t.symbol, volume: t.volume };
      }
    }

    return {
      total,
      up,
      down,
      flat,
      volume,
      tradedValue,
      avgChangePct: changePctSum / total,
      avgRangePct: rangePctSum / total,
      topGain,
      topLoss,
      topVolume,
      latestTs,
    };
  }, [ticks]);

  const upRatio = stats.total > 0 ? (stats.up / stats.total) * 100 : 0;
  const downRatio = stats.total > 0 ? (stats.down / stats.total) * 100 : 0;
  const flatRatio = stats.total > 0 ? (stats.flat / stats.total) * 100 : 0;

  return (
    <aside className="hidden w-80 shrink-0 flex-col rounded-sm border border-zinc-800/50 bg-zinc-900/80 p-3 lg:flex xl:w-96">
      <header className="border-b border-zinc-800/60 pb-2">
        <div className="mb-1 flex items-center justify-between gap-2">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-200">Thống kê tổng quan phiên</h3>
          <span
            className={cn(
              "text-[11px] uppercase tracking-wide",
              connectionStatus === "connected" && "text-emerald-400",
              connectionStatus === "connecting" && "text-amber-400",
              connectionStatus === "disconnected" && "text-zinc-500",
            )}
          >
            {connectionLabel}
          </span>
        </div>
        <p className="text-[11px] text-zinc-500">Cập nhật cuối: {formatTime(stats.latestTs)}</p>
      </header>

      <section className="mt-2 rounded border border-zinc-800/60 bg-zinc-950/60 p-2">
        <p className="mb-2 text-[11px] uppercase tracking-wider text-zinc-500">Độ rộng thị trường</p>
        <div className="mb-2 flex h-2 overflow-hidden rounded bg-zinc-800/80">
          <div className="bg-emerald-500" style={{ width: `${upRatio}%` }} />
          <div className="bg-zinc-500" style={{ width: `${flatRatio}%` }} />
          <div className="bg-rose-500" style={{ width: `${downRatio}%` }} />
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <div className="rounded bg-zinc-900/80 px-1 py-1">
            <p className="text-zinc-500">Tăng</p>
            <p className="font-mono text-emerald-400">{stats.up}</p>
          </div>
          <div className="rounded bg-zinc-900/80 px-1 py-1">
            <p className="text-zinc-500">Đứng</p>
            <p className="font-mono text-zinc-300">{stats.flat}</p>
          </div>
          <div className="rounded bg-zinc-900/80 px-1 py-1">
            <p className="text-zinc-500">Giảm</p>
            <p className="font-mono text-rose-400">{stats.down}</p>
          </div>
        </div>
      </section>

      <section className="mt-2 rounded border border-zinc-800/60 bg-zinc-950/60 p-2">
        <SummaryRow label="Số mã đang theo dõi" value={stats.total.toString()} />
        <SummaryRow label="Tổng KL" value={formatCompact(stats.volume)} />
        <SummaryRow label="GTGD ước tính" value={formatCompact(stats.tradedValue)} />
        <SummaryRow
          label="Biến động TB"
          value={formatPct(stats.avgChangePct)}
          valueClass={statClass(stats.avgChangePct)}
        />
        <SummaryRow
          label="Biên độ TB"
          value={formatPct(stats.avgRangePct)}
          valueClass={stats.avgRangePct > 0 ? "text-amber-300" : "text-zinc-300"}
        />
      </section>

      <section className="mt-2 rounded border border-zinc-800/60 bg-zinc-950/60 p-2">
        <p className="mb-1 text-[11px] uppercase tracking-wider text-zinc-500">Điểm nhấn</p>
        <SummaryRow
          label="Top tăng mạnh"
          value={stats.topGain ? `${stats.topGain.symbol} (${formatPct(stats.topGain.changePct)})` : "—"}
          valueClass={stats.topGain ? "text-emerald-400" : "text-zinc-300"}
        />
        <SummaryRow
          label="Top giảm mạnh"
          value={stats.topLoss ? `${stats.topLoss.symbol} (${formatPct(stats.topLoss.changePct)})` : "—"}
          valueClass={stats.topLoss ? "text-rose-400" : "text-zinc-300"}
        />
        <SummaryRow
          label="KL cao nhất"
          value={stats.topVolume ? `${stats.topVolume.symbol} (${formatCompact(stats.topVolume.volume)})` : "—"}
        />
      </section>

      {stats.total === 0 && (
        <p className="mt-2 rounded border border-zinc-800/60 bg-zinc-950/50 p-2 text-[11px] leading-relaxed text-zinc-500">
          Chưa có dữ liệu phiên. Bấm <span className="text-zinc-300">Load</span> trong Market Data để nạp dữ liệu.
        </p>
      )}
    </aside>
  );
}
