"use client";

import { useEffect } from "react";
import { SectorColumn } from "@/components/sector-column";
import { MarketIndexBar } from "@/components/market-index-bar";
import { DataLoader } from "@/app/(dashboard)/_components/data-loader";
import { TradingErrorBoundary } from "@/components/error-boundary";
import { useMarketStore } from "@/stores/market-store";

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
// Giá tham chiếu thực tế (VND, đơn vị nghìn đồng)
const MOCK_TICKS: Record<string, { price: number; change: number; changePct: number; volume: number }> = {
    // VN30
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
    // BĐS
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
    // Chứng khoán
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
    // Ngân hàng
    VCB:  { price: 85.4,  change: +0.4,  changePct: +0.47, volume: 1_800_000 },
    BID:  { price: 42.1,  change: -0.3,  changePct: -0.71, volume: 2_400_000 },
    STB:  { price: 28.6,  change: +0.6,  changePct: +2.14, volume: 5_600_000 },
    SHB:  { price: 12.8,  change: +0.2,  changePct: +1.59, volume: 4_200_000 },
    HDB:  { price: 18.5,  change: -0.1,  changePct: -0.54, volume: 2_100_000 },
    VIB:  { price: 16.2,  change: +0.4,  changePct: +2.53, volume: 1_800_000 },
    LPB:  { price: 14.8,  change: 0,     changePct: 0,     volume: 3_200_000 },
    TPB:  { price: 15.6,  change: -0.2,  changePct: -1.27, volume: 2_800_000 },
    // Thép
    HSG:  { price: 18.2,  change: -0.4,  changePct: -2.15, volume: 3_400_000 },
    NKG:  { price: 14.5,  change: +0.3,  changePct: +2.11, volume: 1_200_000 },
    SMC:  { price: 12.8,  change: -0.2,  changePct: -1.54, volume: 890_000 },
    TLH:  { price: 8.6,   change: +0.1,  changePct: +1.18, volume: 650_000 },
    TVN:  { price: 16.4,  change: 0,     changePct: 0,     volume: 420_000 },
    POM:  { price: 9.8,   change: -0.3,  changePct: -2.97, volume: 780_000 },
    VGS:  { price: 11.2,  change: +0.2,  changePct: +1.82, volume: 560_000 },
    TNA:  { price: 7.5,   change: -0.1,  changePct: -1.32, volume: 340_000 },
    // Dầu khí
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

export default function MarketBoardPage() {
    const bulkUpdateTicks = useMarketStore((s) => s.bulkUpdateTicks);

    // ★ Inject mock data khi chưa có real WebSocket data
    useEffect(() => {
        const ticks = useMarketStore.getState().ticks;
        const hasRealData = Object.keys(ticks).length > 0;

        if (!hasRealData) {
            // Convert mock data to TickData format
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

    return (
        <div className="flex h-full flex-col bg-[#050508]">
            <MarketIndexBar />
            <DataLoader />

            {/* Board Layout Container */}
            <div className="flex-1 min-h-0 overflow-auto pb-4 pt-2 px-2 custom-scrollbar">
                <div className="flex gap-2 min-w-max h-full items-start">
                    {SECTORS.map((sector) => (
                        <div key={sector.title} className="w-[280px] flex flex-col min-h-0">
                            <TradingErrorBoundary>
                                <SectorColumn title={sector.title} symbols={sector.symbols} />
                            </TradingErrorBoundary>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
