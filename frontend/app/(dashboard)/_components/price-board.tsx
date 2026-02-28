"use client";

/**
 * Price Board — Bảng điện chứng khoán VN.
 * ★ Inspired by sieucophieu.vn/bang-dien.
 * ★ AG Grid với flash animation, bộ lọc sàn, nhiều cột hơn.
 */

import { useCallback, useMemo, useRef, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import { ModuleRegistry, AllCommunityModule } from "ag-grid-community";
import type { ColDef, GridReadyEvent, ICellRendererParams } from "ag-grid-community";
import { useMarketStore } from "@/stores/market-store";
import { useUIStore } from "@/stores/ui-store";
import { cn } from "@/lib/utils";

// ★ VN Exchange symbol lists (approximate — based on actual listings)
// HOSE: 3-letter symbols (most common)
// HNX: 3-letter symbols starting with certain prefixes
// UPCOM: various
const HOSE_SYMBOLS = new Set([
  "FPT","VIC","VHM","GAS","HPG","VPB","MBB","ACB","TCB","SSI","MWG","CTG",
  "VCB","BID","VNM","SAB","MSN","PLX","POW","REE","PNJ","DGC","VHC","HAG",
  "HDB","VIB","STB","SHB","LPB","TPB","OCB","EIB","ABB","BVH","VRE","NVL",
  "PDR","DIG","DXG","KDH","NLG","CEO","SCR","HQC","SJS","VPI","DXS","NRC",
  "HSG","NKG","SMC","TLH","TVN","POM","VGS","TNA","HPX","TIS","VIS",
  "PVD","PVS","BSR","OIL","PVC","PVT","PLC","POS","GAS","PVB","PVG",
]);

const HNX_SYMBOLS = new Set([
  "SHS","MBS","FTS","BSI","CTS","AGR","VIX","ORS","VND","VCI","HCM",
  "PVX","PVC","PVA","HUT","HHC","HGM","HNM","HTC","HVN","IDC","IVS",
  "KSB","L14","LAS","LBM","LCG","LCS","LDG","LEC","LGL","LHC","LIG",
]);

const UPCOM_SYMBOLS = new Set([
  "VGI","ELC","ITD","CMG","VTI","FOX","ONE","VTC","VTL","VTX",
  "ABI","ABT","ACM","ACS","ADC","ADP","ADS","ADT","AEG","AFC",
]);

function getExchangeForSymbol(symbol: string): string {
  if (HOSE_SYMBOLS.has(symbol)) return "HOSE";
  if (HNX_SYMBOLS.has(symbol)) return "HNX";
  if (UPCOM_SYMBOLS.has(symbol)) return "UPCOM";
  // Default: assume HOSE for unknown symbols
  return "HOSE";
}

ModuleRegistry.registerModules([AllCommunityModule]);

// ── Formatters ────────────────────────────────────────────────────────────────

function formatVolume(value: number | undefined): string {
  if (value == null) return "—";
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(0)}K`;
  return value.toString();
}

function formatPrice(value: number | undefined): string {
  if (value == null) return "—";
  return value.toLocaleString("vi-VN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

// ── Cell Renderers ────────────────────────────────────────────────────────────

function PriceCellRenderer(params: ICellRendererParams) {
  const { value, data } = params;
  if (value == null) return <span className="text-zinc-600">—</span>;

  const change = data?.change ?? 0;
  const isCeiling = data?.price >= data?.ceiling && data?.ceiling > 0;
  const isFloor = data?.price <= data?.floor && data?.floor > 0;

  return (
    <span
      className={cn(
        "font-mono tabular-nums font-semibold",
        isCeiling && "price-ceil",
        isFloor && "price-floor",
        !isCeiling && !isFloor && change > 0 && "price-up",
        !isCeiling && !isFloor && change < 0 && "price-down",
        !isCeiling && !isFloor && change === 0 && "price-ref",
      )}
    >
      {formatPrice(value)}
    </span>
  );
}

function ChangeCellRenderer(params: ICellRendererParams) {
  const { value } = params;
  if (value == null) return <span className="text-zinc-600">—</span>;
  const isUp = value > 0;
  const isDown = value < 0;
  return (
    <span className={cn("font-mono tabular-nums", isUp && "price-up", isDown && "price-down", !isUp && !isDown && "text-zinc-500")}>
      {isUp ? "+" : ""}{value.toFixed(2)}
    </span>
  );
}

function ChangePctCellRenderer(params: ICellRendererParams) {
  const { value } = params;
  if (value == null) return <span className="text-zinc-600">—</span>;
  const isUp = value > 0;
  const isDown = value < 0;
  return (
    <span className={cn("font-mono tabular-nums", isUp && "price-up", isDown && "price-down", !isUp && !isDown && "text-zinc-500")}>
      {isUp ? "+" : ""}{value.toFixed(2)}%
    </span>
  );
}

// ── Column Definitions ────────────────────────────────────────────────────────

const columnDefs: ColDef[] = [
  {
    field: "symbol",
    headerName: "Mã CK",
    pinned: "left",
    width: 72,
    sort: "asc",
    cellClass: "font-bold text-amber-300 text-sm cursor-pointer hover:underline",
    headerClass: "text-center",
    tooltipValueGetter: () => "Click để xem biểu đồ kỹ thuật",
  },
  {
    field: "ceiling",
    headerName: "Trần",
    width: 72,
    cellClass: "font-mono text-right price-ceil",
    valueFormatter: (p) => formatPrice(p.value),
    headerClass: "text-right",
  },
  {
    field: "floor",
    headerName: "Sàn",
    width: 72,
    cellClass: "font-mono text-right price-floor",
    valueFormatter: (p) => formatPrice(p.value),
    headerClass: "text-right",
  },
  {
    field: "reference",
    headerName: "TC",
    width: 72,
    cellClass: "font-mono text-right price-ref",
    valueFormatter: (p) => formatPrice(p.value),
    headerClass: "text-right",
  },
  {
    field: "price",
    headerName: "Giá",
    width: 78,
    cellRenderer: PriceCellRenderer,
    headerClass: "text-right",
  },
  {
    field: "change",
    headerName: "+/-",
    width: 68,
    cellRenderer: ChangeCellRenderer,
    headerClass: "text-right",
  },
  {
    field: "changePct",
    headerName: "%",
    width: 64,
    cellRenderer: ChangePctCellRenderer,
    headerClass: "text-right",
  },
  {
    field: "volume",
    headerName: "KL",
    width: 72,
    cellClass: "font-mono text-right text-zinc-300",
    valueFormatter: (p) => formatVolume(p.value as number | undefined),
    headerClass: "text-right",
  },
  {
    field: "high",
    headerName: "Cao",
    width: 72,
    cellClass: "font-mono text-right text-emerald-400/70",
    valueFormatter: (p) => formatPrice(p.value),
    headerClass: "text-right",
    hide: false,
  },
  {
    field: "low",
    headerName: "Thấp",
    width: 72,
    cellClass: "font-mono text-right text-rose-400/70",
    valueFormatter: (p) => formatPrice(p.value),
    headerClass: "text-right",
    hide: false,
  },
];

// ── Exchange Filter ───────────────────────────────────────────────────────────

type ExchangeFilter = "ALL" | "HOSE" | "HNX" | "UPCOM";

const EXCHANGE_TABS: { label: string; value: ExchangeFilter }[] = [
  { label: "Tất cả", value: "ALL" },
  { label: "HOSE", value: "HOSE" },
  { label: "HNX", value: "HNX" },
  { label: "UPCOM", value: "UPCOM" },
];

// ── Main Component ────────────────────────────────────────────────────────────

export function PriceBoard() {
  const gridRef = useRef<AgGridReact>(null);
  const ticks = useMarketStore((s) => s.ticks);
  const openSymbolPopup = useUIStore((s) => s.openSymbolPopup);
  const [exchange, setExchange] = useState<ExchangeFilter>("ALL");
  const [search, setSearch] = useState("");

  const rowData = useMemo(() => {
    let rows = Object.values(ticks);
    if (exchange !== "ALL") {
      // ★ Fix: filter by exchange using symbol lookup tables
      rows = rows.filter((r) => getExchangeForSymbol(r.symbol) === exchange);
    }
    if (search) {
      const q = search.toUpperCase();
      rows = rows.filter((r) => r.symbol.includes(q));
    }
    return rows;
  }, [ticks, exchange, search]);

  const onGridReady = useCallback((_event: GridReadyEvent) => {
    // Grid ready
  }, []);

  const onRowClicked = useCallback(
    (event: { data?: { symbol?: string } }) => {
      if (event.data?.symbol) {
        // ★ Single click → mở popup symbol với chart + chỉ báo kỹ thuật
        openSymbolPopup(event.data.symbol);
      }
    },
    [openSymbolPopup]
  );

  return (
    <div className="flex flex-col h-full">
      {/* ── Filter Bar ── */}
      <div className="flex items-center gap-2 px-2 py-1.5 border-b border-zinc-800/60 shrink-0">
        {/* Exchange tabs */}
        <div className="flex gap-0.5">
          {EXCHANGE_TABS.map((tab) => (
            <button
              key={tab.value}
              onClick={() => setExchange(tab.value)}
              className={cn(
                "px-2 py-0.5 text-xs rounded font-medium transition-colors",
                exchange === tab.value
                  ? "bg-blue-600 text-white"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800",
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search */}
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Tìm mã..."
          className="ml-auto w-24 rounded border border-zinc-700 bg-zinc-900 px-2 py-0.5 text-xs text-zinc-200 placeholder-zinc-600 focus:border-blue-500 focus:outline-none"
        />

        {/* Row count */}
        <span className="text-sm text-zinc-600 shrink-0">
          {rowData.length} mã
        </span>
      </div>

      {/* ── AG Grid ── */}
      <div className="ag-theme-alpine-dark flex-1 min-h-0 price-board">
        <AgGridReact
          ref={gridRef}
          columnDefs={columnDefs}
          rowData={rowData}
          rowBuffer={20}
          getRowId={(params) => params.data.symbol}
          animateRows={false}
          suppressCellFocus={true}
          onGridReady={onGridReady}
          onRowClicked={onRowClicked}
          headerHeight={28}
          rowHeight={26}
          domLayout="normal"
          tooltipShowDelay={300}
          rowClass="cursor-pointer"
        />
      </div>
    </div>
  );
}
