"use client";

import { SectorColumn } from "@/components/sector-column";
import { MarketIndexBar } from "@/components/market-index-bar";
import { DataLoader } from "@/app/(dashboard)/_components/data-loader";

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

            {/* Board Layout Container */}
            <div className="flex-1 overflow-x-auto overflow-y-hidden pb-4 pt-2 px-2 custom-scrollbar">
                <div className="flex gap-2 h-full min-w-max items-start">
                    {SECTORS.map((sector) => (
                        <div key={sector.title} className="w-[320px] h-full flex flex-col">
                            <SectorColumn title={sector.title} symbols={sector.symbols} />
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
