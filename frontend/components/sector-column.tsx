"use client";

import { useMarketStore } from "@/stores/market-store";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";

interface SectorColumnProps {
    title: string;
    symbols: string[];
}

export function SectorColumn({ title, symbols }: SectorColumnProps) {
    const ticks = useMarketStore((s) => s.ticks);
    const router = useRouter();

    // Calculate sector average change based on available symbols
    let totalChangePct = 0;
    let validSymbolsCount = 0;

    const rowData = symbols.map((sym) => {
        const data = ticks[sym];
        if (data && data.changePct !== undefined) {
            totalChangePct += data.changePct;
            validSymbolsCount++;
        }
        return { symbol: sym, data };
    });

    const avgChangePct = validSymbolsCount > 0 ? totalChangePct / validSymbolsCount : 0;
    const isSectorUp = avgChangePct > 0;
    const isSectorDown = avgChangePct < 0;

    return (
        <div className="flex flex-col border border-zinc-800/60 bg-zinc-900/40 rounded-sm overflow-hidden min-w-[200px]">
            {/* Header */}
            <div className="flex items-center justify-between px-3 py-2 bg-zinc-900/80 border-b border-zinc-800 flex-shrink-0">
                <span className="text-sm font-semibold text-zinc-100">{title}</span>
                <span
                    className={cn(
                        "text-xs font-mono font-medium",
                        isSectorUp && "text-emerald-400",
                        isSectorDown && "text-rose-400",
                        !isSectorUp && !isSectorDown && "text-zinc-500"
                    )}
                >
                    {isSectorUp ? "+" : ""}
                    {avgChangePct.toFixed(2)}%
                </span>
            </div>

            {/* List Header */}
            <div className="grid grid-cols-[3fr_3fr_3fr_3fr] gap-2 px-3 py-1.5 bg-zinc-950/50 border-b border-zinc-800/80 text-[10px] font-bold text-zinc-400 uppercase tracking-wider flex-shrink-0">
                <span>Mã</span>
                <span className="text-right">Giá</span>
                <span className="text-right">+/-V</span>
                <span className="text-right">KL</span>
            </div>

            {/* List Items */}
            <div className="flex flex-col overflow-y-auto flex-1">
                {rowData.map(({ symbol, data }) => {
                    const price = data?.price;
                    const changePct = data?.changePct;
                    const volume = data?.volume;

                    const isUp = changePct && changePct > 0;
                    const isDown = changePct && changePct < 0;

                    // Background color for symbol block
                    let symBg = "bg-zinc-800";
                    let symText = "text-zinc-200";

                    if (isUp) {
                        symBg = "bg-emerald-500/20";
                        symText = "text-emerald-400";
                    } else if (isDown) {
                        symBg = "bg-rose-500/20";
                        symText = "text-rose-400";
                    } else if (data) {
                        symBg = "bg-amber-500/20";
                        symText = "text-amber-400";
                    }

                    const formatVolume = (v?: number) => {
                        if (!v) return "—";
                        if (v >= 1000000) return (v / 1000000).toFixed(1) + "m";
                        if (v >= 1000) return (v / 1000).toFixed(1) + "k";
                        return v.toString();
                    };

                    return (
                        <div
                            key={symbol}
                            onClick={() => router.push(`/company/${symbol}`)}
                            className="grid grid-cols-[3fr_3fr_3fr_3fr] gap-2 px-3 py-1.5 border-b border-zinc-800/30 hover:bg-zinc-800/50 transition-colors items-center cursor-pointer"
                        >
                            {/* Mã */}
                            <div
                                className={cn(
                                    "rounded px-1.5 py-0.5 text-xs font-bold w-fit",
                                    symBg,
                                    symText
                                )}
                            >
                                {symbol}
                            </div>

                            {/* Giá */}
                            <div
                                className={cn(
                                    "text-right font-mono text-sm",
                                    isUp && "text-emerald-400",
                                    isDown && "text-rose-400",
                                    !isUp && !isDown && "text-amber-400",
                                    !data && "text-zinc-600"
                                )}
                            >
                                {price ? price.toFixed(2) : "—"}
                            </div>

                            {/* Thay đổi % */}
                            <div
                                className={cn(
                                    "text-right font-mono text-xs",
                                    isUp && "text-emerald-400",
                                    isDown && "text-rose-400",
                                    !isUp && !isDown && "text-amber-400",
                                    !data && "text-zinc-600"
                                )}
                            >
                                {changePct ? (changePct > 0 ? "+" : "") + changePct.toFixed(2) + "%" : "—"}
                            </div>

                            {/* Khối lượng */}
                            <div className="text-right font-mono text-xs text-zinc-300">
                                {formatVolume(volume)}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
