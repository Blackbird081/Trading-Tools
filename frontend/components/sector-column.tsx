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
import { useRef } from "react";

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
    if (changePct > 3) {
        return {
            rowBg: "bg-emerald-900/35 hover:bg-emerald-900/45",
            symbolBg: "bg-emerald-400/45",
            symbolText: "text-emerald-100",
            priceText: "text-emerald-200",
            changeText: "text-emerald-200",
        };
    }
    if (changePct > 1) {
        return {
            rowBg: "bg-emerald-900/25 hover:bg-emerald-900/35",
            symbolBg: "bg-emerald-400/35",
            symbolText: "text-emerald-200",
            priceText: "text-emerald-300",
            changeText: "text-emerald-300",
        };
    }
    if (changePct > 0) {
        return {
            rowBg: "bg-emerald-950/15 hover:bg-emerald-950/28",
            symbolBg: "bg-emerald-500/25",
            symbolText: "text-emerald-300",
            priceText: "text-emerald-400",
            changeText: "text-emerald-400",
        };
    }
    if (changePct < -3) {
        return {
            rowBg: "bg-rose-900/35 hover:bg-rose-900/45",
            symbolBg: "bg-rose-400/45",
            symbolText: "text-rose-100",
            priceText: "text-rose-200",
            changeText: "text-rose-200",
        };
    }
    if (changePct < -1) {
        return {
            rowBg: "bg-rose-900/25 hover:bg-rose-900/35",
            symbolBg: "bg-rose-400/35",
            symbolText: "text-rose-200",
            priceText: "text-rose-300",
            changeText: "text-rose-300",
        };
    }
    if (changePct < 0) {
        return {
            rowBg: "bg-rose-950/15 hover:bg-rose-950/28",
            symbolBg: "bg-rose-500/25",
            symbolText: "text-rose-300",
            priceText: "text-rose-400",
            changeText: "text-rose-400",
        };
    }
    // Reference price (changePct === 0)
    return {
        rowBg: "bg-amber-950/14 hover:bg-amber-950/26",
        symbolBg: "bg-amber-500/20",
        symbolText: "text-amber-200",
        priceText: "text-amber-300",
        changeText: "text-amber-300",
    };
}

function getHeaderGradient(changePct: number) {
    if (changePct > 2) return "from-emerald-900/80 to-zinc-900/90";
    if (changePct > 0.5) return "from-emerald-950/80 to-zinc-900/90";
    if (changePct > 0) return "from-emerald-950/55 to-zinc-900/90";
    if (changePct < -2) return "from-rose-900/80 to-zinc-900/90";
    if (changePct < -0.5) return "from-rose-950/80 to-zinc-900/90";
    if (changePct < 0) return "from-rose-950/55 to-zinc-900/90";
    return "from-zinc-900/90 to-zinc-900/90";
}

// ── Component ─────────────────────────────────────────────────────────────────

export function SectorColumn({ title, symbols }: SectorColumnProps) {
    const ticks = useMarketStore((s) => s.ticks);
    const openSymbolPopup = useUIStore((s) => s.openSymbolPopup);
    const touchStartRef = useRef<{ x: number; y: number } | null>(null);
    const movedRef = useRef(false);

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
    const headerGradient = getHeaderGradient(avgChangePct);

    const handleRowsTouchStart = (e: React.TouchEvent<HTMLDivElement>) => {
        const touch = e.touches[0];
        if (!touch) return;
        touchStartRef.current = { x: touch.clientX, y: touch.clientY };
        movedRef.current = false;
    };

    const handleRowsTouchMove = (e: React.TouchEvent<HTMLDivElement>) => {
        const touch = e.touches[0];
        const start = touchStartRef.current;
        if (!touch || !start) return;
        if (Math.abs(touch.clientX - start.x) > 8 || Math.abs(touch.clientY - start.y) > 8) {
            movedRef.current = true;
        }
    };

    const handleRowsTouchEnd = () => {
        touchStartRef.current = null;
    };

    const handleRowClick = (symbol: string) => {
        // Prevent accidental popup open while user is swiping/scrolling the list.
        if (movedRef.current) return;
        openSymbolPopup(symbol);
    };

    return (
        <div className="flex flex-col overflow-hidden rounded border border-zinc-700/50 shadow-lg md:max-h-[calc(100vh-130px)]">
            {/* ── Sector Header ── */}
            <div className={cn(
                "flex shrink-0 items-center justify-between bg-gradient-to-r px-3 py-2.5 md:py-2",
                headerGradient,
                "border-b border-zinc-700/60"
            )}>
                <span className="text-sm font-bold uppercase tracking-wide text-zinc-100 md:text-xs">
                    {title}
                </span>
                <div className="flex items-center gap-1.5">
                    {/* Sector trend indicator */}
                    <span className={cn(
                        "font-mono text-sm font-semibold md:text-xs",
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
            <div className="grid shrink-0 grid-cols-[2.5fr_2.5fr_2.5fr_2fr] border-b border-zinc-700/60 bg-zinc-900 px-2.5 py-1.5 md:px-2 md:py-1">
                <span className="text-[11px] font-bold uppercase tracking-widest text-zinc-500 md:text-[9px]">Mã</span>
                <span className="text-right text-[11px] font-bold uppercase tracking-widest text-zinc-500 md:text-[9px]">Giá</span>
                <span className="text-right text-[11px] font-bold uppercase tracking-widest text-zinc-500 md:text-[9px]">%</span>
                <span className="text-right text-[11px] font-bold uppercase tracking-widest text-zinc-500 md:text-[9px]">KL</span>
            </div>

            {/* ── Stock Rows ── */}
            <div
                className="max-h-[calc(100dvh-260px)] overflow-y-auto overscroll-contain touch-pan-y bg-zinc-950 [-webkit-overflow-scrolling:touch] md:max-h-none md:flex-1 md:overflow-y-auto"
                onTouchStart={handleRowsTouchStart}
                onTouchMove={handleRowsTouchMove}
                onTouchEnd={handleRowsTouchEnd}
            >
                {rowData.map(({ symbol, data }) => {
                    const colors = getRowColors(data?.changePct, !!data);

                    return (
                        <div
                            key={symbol}
                            onClick={() => handleRowClick(symbol)}
                            className={cn(
                                "grid grid-cols-[2.5fr_2.5fr_2.5fr_2fr] px-2.5 py-2 md:px-2 md:py-[5px]",
                                "border-b border-zinc-800/40 cursor-pointer transition-colors",
                                colors.rowBg,
                            )}
                        >
                            {/* Mã CK */}
                            <div className="flex items-center">
                                <span className={cn(
                                    "rounded-sm px-1.5 py-0.5 text-xs font-bold md:px-1 md:text-[11px]",
                                    colors.symbolBg,
                                    colors.symbolText,
                                )}>
                                    {symbol}
                                </span>
                            </div>

                            {/* Giá */}
                            <div className={cn(
                                "self-center text-right font-mono text-sm font-semibold tabular-nums md:text-[11px]",
                                colors.priceText,
                            )}>
                                {formatPrice(data?.price)}
                            </div>

                            {/* % thay đổi */}
                            <div className={cn(
                                "self-center text-right font-mono text-xs tabular-nums md:text-[10px]",
                                colors.changeText,
                            )}>
                                {formatChangePct(data?.changePct)}
                            </div>

                            {/* Khối lượng */}
                            <div className="self-center text-right font-mono text-xs text-zinc-500 tabular-nums md:text-[10px]">
                                {formatVolume(data?.volume)}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
