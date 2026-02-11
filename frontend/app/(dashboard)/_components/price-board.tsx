"use client";

import { useCallback, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import { AgGridReact } from "ag-grid-react";
import { ModuleRegistry, AllCommunityModule } from "ag-grid-community";
import type { ColDef, GridReadyEvent } from "ag-grid-community";
import { useMarketStore } from "@/stores/market-store";
import { useUIStore } from "@/stores/ui-store";

ModuleRegistry.registerModules([AllCommunityModule]);

function formatVolume(value: number | undefined): string {
  if (value == null) return "—";
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toString();
}

function formatPrice(value: number | undefined): string {
  if (value == null) return "—";
  return value.toLocaleString("vi-VN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

const columnDefs: ColDef[] = [
  {
    field: "symbol",
    headerName: "Mã",
    pinned: "left",
    width: 82,
    sort: "asc",
    cellClass: "font-bold text-amber-300",
  },
  {
    field: "ceiling",
    headerName: "Trần",
    width: 78,
    cellClass: "font-mono text-right text-fuchsia-300",
    valueFormatter: (p) => formatPrice(p.value),
  },
  {
    field: "floor",
    headerName: "Sàn",
    width: 78,
    cellClass: "font-mono text-right text-cyan-300",
    valueFormatter: (p) => formatPrice(p.value),
  },
  {
    field: "reference",
    headerName: "TC",
    width: 78,
    cellClass: "font-mono text-right text-yellow-300",
    valueFormatter: (p) => formatPrice(p.value),
  },
  {
    field: "price",
    headerName: "Giá",
    width: 82,
    cellClassRules: {
      "font-mono text-right font-semibold price-up": (p) =>
        (p.data?.change ?? 0) > 0,
      "font-mono text-right font-semibold price-down": (p) =>
        (p.data?.change ?? 0) < 0,
      "font-mono text-right font-semibold price-ref": (p) =>
        (p.data?.change ?? 0) === 0,
    },
    valueFormatter: (p) => formatPrice(p.value),
  },
  {
    field: "change",
    headerName: "+/-",
    width: 75,
    cellClassRules: {
      "font-mono text-right font-semibold price-up": (p) =>
        (p.value ?? 0) > 0,
      "font-mono text-right font-semibold price-down": (p) =>
        (p.value ?? 0) < 0,
      "font-mono text-right text-zinc-500": (p) => (p.value ?? 0) === 0,
    },
    valueFormatter: (p) => {
      const v = p.value as number | undefined;
      if (v == null) return "—";
      return v > 0 ? `+${v.toFixed(2)}` : v.toFixed(2);
    },
  },
  {
    field: "changePct",
    headerName: "%",
    width: 72,
    cellClassRules: {
      "font-mono text-right text-xs price-up": (p) => (p.value ?? 0) > 0,
      "font-mono text-right text-xs price-down": (p) => (p.value ?? 0) < 0,
      "font-mono text-right text-xs text-zinc-500": (p) =>
        (p.value ?? 0) === 0,
    },
    valueFormatter: (p) => {
      const v = p.value as number | undefined;
      if (v == null) return "—";
      return v > 0 ? `+${v.toFixed(1)}%` : `${v.toFixed(1)}%`;
    },
  },
  {
    field: "volume",
    headerName: "KL",
    width: 82,
    cellClass: "font-mono text-right text-zinc-200",
    valueFormatter: (p) => formatVolume(p.value as number | undefined),
  },
];

export function PriceBoard() {
  const gridRef = useRef<AgGridReact>(null);
  const router = useRouter();
  const ticks = useMarketStore((s) => s.ticks);
  const setActiveSymbol = useUIStore((s) => s.setActiveSymbol);

  const rowData = useMemo(() => Object.values(ticks), [ticks]);

  const onGridReady = useCallback((_event: GridReadyEvent) => {
    // Grid is ready
  }, []);

  const onRowClicked = useCallback(
    (event: { data?: { symbol?: string } }) => {
      if (event.data?.symbol) {
        setActiveSymbol(event.data.symbol);
      }
    },
    [setActiveSymbol]
  );

  const onRowDoubleClicked = useCallback(
    (event: { data?: { symbol?: string } }) => {
      if (event.data?.symbol) {
        router.push(`/company/${event.data.symbol}`);
      }
    },
    [router]
  );

  return (
    <div className="ag-theme-alpine-dark h-full w-full price-board">
      <AgGridReact
        ref={gridRef}
        columnDefs={columnDefs}
        rowData={rowData}
        rowBuffer={10}
        getRowId={(params) => params.data.symbol}
        animateRows={false}
        suppressCellFocus={true}
        onGridReady={onGridReady}
        onRowClicked={onRowClicked}
        onRowDoubleClicked={onRowDoubleClicked}
        headerHeight={34}
        rowHeight={32}
        domLayout="normal"
        tooltipShowDelay={300}
      />
    </div>
  );
}
