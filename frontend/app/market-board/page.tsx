"use client";

import { useEffect, useState } from "react";
import { SectorColumn } from "@/components/sector-column";
import { MarketIndexBar } from "@/components/market-index-bar";
import { DataLoader } from "@/app/(dashboard)/_components/data-loader";
import { TradingErrorBoundary } from "@/components/error-boundary";
import { useMarketStore } from "@/stores/market-store";
import { ChevronLeft, ChevronRight } from "lucide-react";

const SECTORS = [
    {
        title: "VN30",
        symbols: ["FPT", "VIC", "VHM", "GAS", "HPG", "VPB", "MBB", "ACB", "TCB", "SSI", "MWG", "CTG"],
    },
    {
        title: "Bất động sản",
        symbols: ["VHM", "VIC", "NVL", "PDR", "DIG", "DXG", "KDH", "NLG", "CEO", "SCR", "HQC", "SJS"],
    },
    {
        title: "Chứng khoán",
        symbols: ["SSI", "VND", "VCI", "HCM", "SHS", "MBS", "FTS", "BSI", "CTS", "AGR", "VIX", "ORS"],
    },
    {
        title: "Ngân hàng",
        symbols: ["VCB", "BID", "CTG", "TCB", "MBB", "VPB", "ACB", "STB", "SHB", "HDB", "VIB", "LPB", "TPB"],
    },
    {
        title: "Thép",
        symbols: ["HPG", "HSG", "NKG", "SMC", "TLH", "TVN", "POM", "VGS", "TNA"],
    },
    {
        title: "Dầu khí",
        symbols: ["GAS", "PVD", "PVS", "BSR", "PLX", "OIL", "PVC", "PVT", "PLC", "POS"],
    },
];

// ★ Mock data để test giao diện khi chưa có real data từ WebSocket
const MOCK_TICKS: Record<string, { price: number; change: number; changePct: number; volume: number }> = {
    FPT:  { price: 98.5,  change: +1.2,  changePct: +1.23, volume: 2_850_000 },
    VIC:  { price: 42.3,  change: -0.5,  changePct: -1.17, volume: 1_200_000 },
    VHM:  { price: 38.1,  change: +0.3,  changePct: +0.79, volume: 3_100_000 },
    GAS:  { price: 65.2,  change: 0,     changePct: 0,     volume: 890_000 },
    HPG:  { price: 25.8,  change: -0.8,  changePct: -3.01, volume: 8_500_000 },
    VPB:  { price: 18.4,  change: +0.4,  changePct: +2.22, volume: 5_200_000 },
    MBB:  { price: 22.1,  change: +0.1,  changePct: +0.45, volume: 4_800_000 },
    ACB:  { price: 24.5,  change: -0.2,  changePct: -0.81, volume: 3_600_000 },
    TCB:  { price: 19.8,  change: +0.6,  changePct: +3.12, volume: 6_100_000 },
    SSI:  { price: 28.3,  change: +0.8,  changePct: +2.91, volume: 2_400_000 },
    MWG:  { price: 52.4,  change: -1.1,  changePct: -2.06, volume: 1_800_000 },
    CTG:  { price: 31.2,  change: +0.2,  changePct: +0.64, volume: 4_200_000 },
    NVL:  { price: 12.5,  change: -0.3,  changePct: -2.34, volume: 2_100_000 },
    PDR:  { price: 15.8,  change: +0.5,  changePct: +3.27, volume: 1_500_000 },
    DIG:  { price: 18.2,  change: +0.2,  changePct: +1.11, volume: 980_000 },
    DXG:  { price: 11.4,  change: -0.1,  changePct: -0.87, volume: 1_200_000 },
    KDH:  { price: 22.6,  change: +0.4,  changePct: +1.80, volume: 750_000 },
    NLG:  { price: 28.9,  change: 0,     changePct: 0,     volume: 620_000 },
    CEO:  { price: 8.5,   change: -0.2,  changePct: -2.30, volume: 890_000 },
    SCR:  { price: 6.8,   change: +0.1,  changePct: +1.49, volume: 450_000 },
    HQC:  { price: 3.2,   change: -0.1,  changePct: -3.03, volume: 2_300_000 },
    SJS:  { price: 45.6,  change: +1.2,  changePct: +2.70, volume: 320_000 },
    VND:  { price: 18.6,  change: +0.6,  changePct: +3.33, volume: 3_800_000 },
    VCI:  { price: 32.4,  change: +0.4,  changePct: +1.25, volume: 1_200_000 },
    HCM:  { price: 22.8,  change: -0.3,  changePct: -1.30, volume: 980_000 },
    SHS:  { price: 12.1,  change: +0.2,  changePct: +1.68, volume: 2_100_000 },
    MBS:  { price: 15.4,  change: 0,     changePct: 0,     volume: 650_000 },
    FTS:  { price: 19.8,  change: +0.8,  changePct: +4.21, volume: 1_400_000 },
    BSI:  { price: 24.5,  change: -0.5,  changePct: -2.00, volume: 780_000 },
    CTS:  { price: 16.2,  change: +0.2,  changePct: +1.25, volume: 560_000 },
    AGR:  { price: 8.9,   change: -0.1,  changePct: -1.11, volume: 1_200_000 },
    VIX:  { price: 11.5,  change: +0.3,  changePct: +2.68, volume: 3_200_000 },
    ORS:  { price: 14.8,  change: +0.4,  changePct: +2.78, volume: 890_000 },
    VCB:  { price: 85.4,  change: +0.4,  changePct: +0.47, volume: 1_800_000 },
    BID:  { price: 42.1,  change: -0.3,  changePct: -0.71, volume: 2_400_000 },
    STB:  { price: 28.6,  change: +0.6,  changePct: +2.14, volume: 5_600_000 },
    SHB:  { price: 12.8,  change: +0.2,  changePct: +1.59, volume: 4_200_000 },
    HDB:  { price: 18.5,  change: -0.1,  changePct: -0.54, volume: 2_100_000 },
    VIB:  { price: 16.2,  change: +0.4,  changePct: +2.53, volume: 1_800_000 },
    LPB:  { price: 14.8,  change: 0,     changePct: 0,     volume: 3_200_000 },
    TPB:  { price: 15.6,  change: -0.2,  changePct: -1.27, volume: 2_800_000 },
    HSG:  { price: 18.2,  change: -0.4,  changePct: -2.15, volume: 3_400_000 },
    NKG:  { price: 14.5,  change: +0.3,  changePct: +2.11, volume: 1_200_000 },
    SMC:  { price: 12.8,  change: -0.2,  changePct: -1.54, volume: 890_000 },
    TLH:  { price: 8.6,   change: +0.1,  changePct: +1.18, volume: 650_000 },
    TVN:  { price: 16.4,  change: 0,     changePct: 0,     volume: 420_000 },
    POM:  { price: 9.8,   change: -0.3,  changePct: -2.97, volume: 780_000 },
    VGS:  { price: 11.2,  change: +0.2,  changePct: +1.82, volume: 560_000 },
    TNA:  { price: 7.5,   change: -0.1,  changePct: -1.32, volume: 340_000 },
    PVD:  { price: 18.6,  change: +0.6,  changePct: +3.33, volume: 2_800_000 },
    PVS:  { price: 28.4,  change: +0.4,  changePct: +1.43, volume: 1_600_000 },
    BSR:  { price: 12.8,  change: -0.2,  changePct: -1.54, volume: 980_000 },
    PLX:  { price: 42.5,  change: +0.5,  changePct: +1.19, volume: 1_200_000 },
    OIL:  { price: 8.9,   change: -0.1,  changePct: -1.11, volume: 650_000 },
    PVC:  { price: 6.8,   change: +0.2,  changePct: +3.03, volume: 890_000 },
    PVT:  { price: 18.2,  change: +0.2,  changePct: +1.11, volume: 780_000 },
    PLC:  { price: 24.5,  change: -0.5,  changePct: -2.00, volume: 420_000 },
    POS:  { price: 15.6,  change: +0.4,  changePct: +2.63, volume: 560_000 },
};

// ★ Pagination: 3 sectors per page on desktop
const SECTORS_PER_PAGE = 3;
const TOTAL_PAGES = Math.ceil(SECTORS.length / SECTORS_PER_PAGE);

export default function MarketBoardPage() {
    const bulkUpdateTicks = useMarketStore((s) => s.bulkUpdateTicks);
    const [currentPage, setCurrentPage] = useState(0);  // 0-indexed

    // ★ Inject mock data khi chưa có real WebSocket data
    useEffect(() => {
        const ticks = useMarketStore.getState().ticks;
        const hasRealData = Object.keys(ticks).length > 0;

        if (!hasRealData) {
            const mockTickArray = Object.entries(MOCK_TICKS).map(([symbol, d]) => ({
                symbol,
                price: d.price,
                change: d.change,
                changePct: d.changePct,
                volume: d.volume,
                high: d.price + Math.abs(d.change) * 1.5,
                low: d.price - Math.abs(d.change) * 1.5,
                open: d.price - d.change,
                ceiling: d.price * 1.07,
                floor: d.price * 0.93,
                reference: d.price - d.change,
                timestamp: Date.now(),
            }));
            bulkUpdateTicks(mockTickArray);
        }
    }, [bulkUpdateTicks]);

    // Current page sectors
    const startIdx = currentPage * SECTORS_PER_PAGE;
    const pageSectors = SECTORS.slice(startIdx, startIdx + SECTORS_PER_PAGE);

    const goToPrev = () => setCurrentPage((p) => Math.max(0, p - 1));
    const goToNext = () => setCurrentPage((p) => Math.min(TOTAL_PAGES - 1, p + 1));

    return (
        <div className="flex flex-col bg-[#050508] h-full">
            <DataLoader />

            {/* ★ Desktop: Pagination navigation bar */}
            <div className="hidden md:flex items-center justify-between px-3 py-1.5 bg-zinc-900/60 border-b border-zinc-800/60 shrink-0">
                {/* Page indicator dots */}
                <div className="flex items-center gap-2">
                    {Array.from({ length: TOTAL_PAGES }).map((_, i) => (
                        <button
                            key={i}
                            onClick={() => setCurrentPage(i)}
                            className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                                i === currentPage
                                    ? "bg-blue-600 text-white"
                                    : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200"
                            }`}
                        >
                            Trang {i + 1}
                            <span className="text-[10px] opacity-70">
                                ({SECTORS.slice(i * SECTORS_PER_PAGE, (i + 1) * SECTORS_PER_PAGE).map(s => s.title).join(", ")})
                            </span>
                        </button>
                    ))}
                </div>

                {/* Prev / Next buttons */}
                <div className="flex items-center gap-1">
                    <button
                        onClick={goToPrev}
                        disabled={currentPage === 0}
                        className="flex items-center gap-1 px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-zinc-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-xs"
                    >
                        <ChevronLeft className="w-3.5 h-3.5" />
                        Trước
                    </button>
                    <span className="text-xs text-zinc-600 px-1">
                        {currentPage + 1} / {TOTAL_PAGES}
                    </span>
                    <button
                        onClick={goToNext}
                        disabled={currentPage === TOTAL_PAGES - 1}
                        className="flex items-center gap-1 px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-zinc-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-xs"
                    >
                        Tiếp
                        <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                </div>
            </div>

            {/* ★ Desktop: 3 columns per page — fill full width */}
            <div className="hidden md:flex flex-1 min-h-0 gap-2 p-2">
                {pageSectors.map((sector) => (
                    <div key={sector.title} className="flex-1 min-w-0 flex flex-col">
                        <TradingErrorBoundary>
                            <SectorColumn title={sector.title} symbols={sector.symbols} />
                        </TradingErrorBoundary>
                    </div>
                ))}
                {/* Fill empty slots if last page has < 3 sectors */}
                {pageSectors.length < SECTORS_PER_PAGE && Array.from({ length: SECTORS_PER_PAGE - pageSectors.length }).map((_, i) => (
                    <div key={`empty-${i}`} className="flex-1 min-w-0" />
                ))}
            </div>

            {/* ★ Mobile: vertical scroll layout */}
            <div className="flex md:hidden flex-1 min-h-0 overflow-y-auto flex-col px-2 py-2 gap-3">
                {SECTORS.map((sector) => (
                    <TradingErrorBoundary key={sector.title}>
                        <SectorColumn title={sector.title} symbols={sector.symbols} />
                    </TradingErrorBoundary>
                ))}
            </div>

            {/* ★ Market Index Bar — đặt ở dưới cùng như footer */}
            <div className="shrink-0 border-t border-zinc-800/60">
                <MarketIndexBar />
            </div>
        </div>
    );
}
