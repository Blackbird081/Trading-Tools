"use client";

/**
 * SectorColumn — Cột ngành trong Market Board.
 * ★ Inspired by sieucophieu.vn/bang-dien sector columns.
 * ★ Compact rows, color-coded by price movement.
 * ★ Header shows sector name + average change %.
 */

import { useMarketStore } from "@/stores/market-store";
import { useUIStore } from "@/stores/ui-store";
import { cn } from "@/lib/utils";

interface SectorColumnProps {
    title: string;
    symbols: string[];
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatVolume(v?: number): string {
    if (v == null || v === 0) return "—";
    if (v >= 1_000_000) return (v / 1_000_000).toFixed(1) + "M";
    if (v >= 1_000) return (v / 1_000).toFixed(0) + "K";
    return v.toString();
}

function formatPrice(v?: number): string {
    if (v == null) return "—";
    // VN stocks: prices in thousands VND, show 2 decimal
    return v.toFixed(2);
}

function formatChangePct(v?: number): string {
    if (v == null) return "—";
    const sign = v > 0 ? "+" : "";
    return `${sign}${v.toFixed(2)}%`;
}

// ── Row color based on price movement ────────────────────────────────────────
// sieucophieu.vn style: subtle background tint per row

function getRowColors(changePct?: number, hasData?: boolean) {
    if (!hasData) {
        return {
            rowBg: "",
            symbolBg: "bg-zinc-800/60",
            symbolText: "text-zinc-500",
            priceText: "text-zinc-600",
            changeText: "text-zinc-600",
        };
    }
    if (changePct == null) {
        return {
            rowBg: "bg-amber-950/10",
            symbolBg: "bg-amber-500/20",
            symbolText: "text-amber-300",
            priceText: "text-amber-300",
            changeText: "text-amber-400",
        };
    }
    if (changePct > 0) {
        return {
            rowBg: "bg-emerald-950/20 hover:bg-emerald-950/40",
            symbolBg: "bg-emerald-500/25",
            symbolText: "text-emerald-300",
            priceText: "text-emerald-400",
            changeText: "text-emerald-400",
        };
    }
    if (changePct < 0) {
        return {
            rowBg: "bg-rose-950/20 hover:bg-rose-950/40",
            symbolBg: "bg-rose-500/25",
            symbolText: "text-rose-300",
            priceText: "text-rose-400",
            changeText: "text-rose-400",
        };
    }
    // Reference price (changePct === 0)
    return {
        rowBg: "bg-amber-950/10 hover:bg-amber-950/25",
        symbolBg: "bg-amber-500/20",
        symbolText: "text-amber-300",
        priceText: "text-amber-300",
        changeText: "text-amber-400",
    };
}

// ── Component ─────────────────────────────────────────────────────────────────

export function SectorColumn({ title, symbols }: SectorColumnProps) {
    const ticks = useMarketStore((s) => s.ticks);
    const openSymbolPopup = useUIStore((s) => s.openSymbolPopup);

    // Calculate sector average change
    let totalChangePct = 0;
    let validCount = 0;

    const rowData = symbols.map((sym) => {
        const data = ticks[sym];
        if (data?.changePct != null) {
            totalChangePct += data.changePct;
            validCount++;
        }
        return { symbol: sym, data };
    });

    const avgChangePct = validCount > 0 ? totalChangePct / validCount : 0;
    const isSectorUp = avgChangePct > 0.001;
    const isSectorDown = avgChangePct < -0.001;

    // Header gradient based on sector performance
    const headerGradient = isSectorUp
        ? "from-emerald-950/80 to-zinc-900/90"
        : isSectorDown
            ? "from-rose-950/80 to-zinc-900/90"
            : "from-zinc-900/90 to-zinc-900/90";

    return (
        <div className="flex flex-col rounded overflow-hidden border border-zinc-700/50 shadow-lg md:max-h-[calc(100vh-130px)]">
            {/* ── Sector Header ── */}
            <div className={cn(
                "flex items-center justify-between px-3 py-2 bg-gradient-to-r flex-shrink-0",
                headerGradient,
                "border-b border-zinc-700/60"
            )}>
                <span className="text-xs font-bold text-zinc-100 uppercase tracking-wide">
                    {title}
                </span>
                <div className="flex items-center gap-1.5">
                    {/* Sector trend indicator */}
                    <span className={cn(
                        "text-xs font-mono font-semibold",
                        isSectorUp && "text-emerald-400",
                        isSectorDown && "text-rose-400",
                        !isSectorUp && !isSectorDown && "text-amber-400",
                    )}>
                        {isSectorUp ? "▲" : isSectorDown ? "▼" : "—"}
                        {" "}{Math.abs(avgChangePct).toFixed(2)}%
                    </span>
                </div>
            </div>

            {/* ── Column Headers ── */}
            <div className="grid grid-cols-[2.5fr_2.5fr_2.5fr_2fr] px-2 py-1 bg-zinc-900 border-b border-zinc-700/60 flex-shrink-0">
                <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest">Mã</span>
                <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest text-right">Giá</span>
                <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest text-right">%</span>
                <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest text-right">KL</span>
            </div>

            {/* ── Stock Rows ── */}
            <div className="flex flex-col overflow-y-auto flex-1 bg-zinc-950">
                {rowData.map(({ symbol, data }) => {
                    const colors = getRowColors(data?.changePct, !!data);

                    return (
                        <div
                            key={symbol}
                            onClick={() => openSymbolPopup(symbol)}
                            className={cn(
                                "grid grid-cols-[2.5fr_2.5fr_2.5fr_2fr] px-2 py-[5px]",
                                "border-b border-zinc-800/40 cursor-pointer transition-colors",
                                colors.rowBg,
                            )}
                        >
                            {/* Mã CK */}
                            <div className="flex items-center">
                                <span className={cn(
                                    "text-[11px] font-bold px-1 py-0.5 rounded-sm",
                                    colors.symbolBg,
                                    colors.symbolText,
                                )}>
                                    {symbol}
                                </span>
                            </div>

                            {/* Giá */}
                            <div className={cn(
                                "text-right font-mono text-[11px] tabular-nums font-semibold self-center",
                                colors.priceText,
                            )}>
                                {formatPrice(data?.price)}
                            </div>

                            {/* % thay đổi */}
                            <div className={cn(
                                "text-right font-mono text-[10px] tabular-nums self-center",
                                colors.changeText,
                            )}>
                                {formatChangePct(data?.changePct)}
                            </div>

                            {/* Khối lượng */}
                            <div className="text-right font-mono text-[10px] text-zinc-500 tabular-nums self-center">
                                {formatVolume(data?.volume)}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
