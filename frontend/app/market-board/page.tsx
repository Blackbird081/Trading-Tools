"use client";

import { SectorColumn } from "@/components/sector-column";
import { MarketIndexBar } from "@/components/market-index-bar";
import { DataLoader } from "@/app/(dashboard)/_components/data-loader";
import { TradingErrorBoundary } from "@/components/error-boundary";

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

export default function MarketBoardPage() {
    return (
        <div className="flex h-full flex-col bg-[#050508]">
            <MarketIndexBar />
            <DataLoader />

            {/* ★ Fix: Board Layout Container — thanh cuộn ngang hiển thị đúng */}
            {/* Dùng overflow-auto thay vì overflow-x-auto + overflow-y-hidden */}
            {/* min-h-0 để flex child có thể shrink đúng cách */}
            <div className="flex-1 min-h-0 overflow-auto pb-4 pt-2 px-2">
                {/* min-w-max đảm bảo container không bị co lại, kích hoạt scroll ngang */}
                <div className="flex gap-2 min-w-max h-full items-start">
                    {SECTORS.map((sector) => (
                        // ★ Fix: bỏ h-full, dùng flex-col + min-h-0 để column scroll đúng
                        <div key={sector.title} className="w-[300px] flex flex-col min-h-0">
                            {/* ★ Fix: wrap với Error Boundary để 1 column crash không ảnh hưởng cột khác */}
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
