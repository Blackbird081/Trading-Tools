# 03 — FRONTEND ARCHITECTURE

**Project:** Multi-Task Algorithmic Trading System (Enterprise Edition)
**Role:** Senior Frontend Engineer (React / Next.js Expert)
**Version:** 1.0 | February 2026
**Stack:** Next.js 15 (App Router) | React 19 | TypeScript 5.6 (strict) | Tailwind CSS 4

---

## 1. NEXT.JS APP ROUTER STRATEGY

### 1.1. Server Components vs Client Components — Architectural Boundaries

In a trading terminal, **most of the UI is real-time** — but not all of it. App Router allows precise separation:

```
┌─────────────────────────────────────────────────────────────────┐
│                    SERVER COMPONENTS (RSC)                       │
│ Render once on the server → stream HTML → do not ship JS │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  Root    │  │ Sidebar  │  │ Top Nav  │  │ Settings │       │
│  │  Layout  │  │ (static) │  │ (user    │  │ Page     │       │
│  │          │  │          │  │  info)   │  │          │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│                                                                 │
│ Payload: 0 KB JavaScript for these components │
├─────────────────────────────────────────────────────────────────┤
│                    CLIENT COMPONENTS ("use client")              │
│ Hydrate on browser → maintain state → WebSocket connection │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Price    │  │ Trading  │  │ Order    │  │ Command  │       │
│  │ Board    │  │ Chart    │  │ Book     │  │ Palette  │       │
│  │ (AG Grid)│  │ (Canvas) │  │ (form)   │  │ (Ctrl+K) │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│                                                                 │
│  Payload: ~150-250 KB JS (AG Grid + Chart lib + Zustand)        │
└─────────────────────────────────────────────────────────────────┘
```

#### Classification rules

|Criteria| Server Component | Client Component |
|:---|:---|:---|
|Need WebSocket / real-time data?| ❌ | ✅ |
|Need browser API (Canvas, DOM events)?| ❌ | ✅ |
|Need `useState`, `useEffect`?| ❌ | ✅ |
|Change < 1 time/minute?| ✅ | ❌ |
|Contains sensitive logic (API keys)?| ✅ | ❌ |

### 1.2. Route Structure

```
frontend/
└── app/
    ├── layout.tsx              # ★ ROOT LAYOUT (Server Component)
    │                           #   Persistent shell: sidebar + topnav
    │                           #   Renders ONCE, never re-mounts on navigation
    │
    ├── (dashboard)/
    │   ├── layout.tsx          # Dashboard sub-layout (Server)
    │   ├── page.tsx            # Default view: Watchlist + Chart (Server → delegates to Client)
    │   └── _components/
    │       ├── price-board.tsx  # "use client" — AG Grid wrapper
    │       ├── trading-chart.tsx# "use client" — TradingView wrapper
    │       └── mini-portfolio.tsx # "use client" — sidebar widget
    │
    ├── portfolio/
    │   ├── page.tsx            # Portfolio overview (Server: fetch initial data)
    │   └── _components/
    │       ├── positions-table.tsx  # "use client" — AG Grid
    │       └── pnl-chart.tsx       # "use client" — Canvas chart
    │
    ├── screener/
    │   ├── page.tsx            # Screener filters (Server shell)
    │   └── _components/
    │       └── screener-grid.tsx   # "use client" — AG Grid + filters
    │
    ├── orders/
    │   ├── page.tsx            # Order management
    │   └── _components/
    │       ├── order-form.tsx      # "use client" — form + validation
    │       └── order-history.tsx   # "use client" — AG Grid
    │
    └── settings/
        └── page.tsx            # ★ Fully Server Component — no JS shipped
```

### 1.3. Persistent Layouts — Why Trading Terminal is critical

```tsx
// app/layout.tsx — Server Component (ROOT)
// ★ This component NEVER re-renders on route change.
// Sidebar, topnav, WebSocket provider persist across all pages.

import { Sidebar } from "@/components/sidebar";
import { TopNav } from "@/components/top-nav";
import { WebSocketProvider } from "@/providers/ws-provider";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi" className="dark">
      <body className="bg-zinc-950 text-zinc-100">
        <WebSocketProvider>
          <div className="flex h-screen">
            <Sidebar />
            <div className="flex flex-1 flex-col">
              <TopNav />
              <main className="flex-1 overflow-hidden">
                {children}
              </main>
            </div>
          </div>
        </WebSocketProvider>
      </body>
    </html>
  );
}
```

**Why Persistent Layout is important:**
- When the user switches from `/dashboard` to `/portfolio`, React **does not unmount** `RootLayout`. WebSocket connection in `WebSocketProvider` **not broken**.
- Sidebar watchlist widget continues to receive ticks without needing to reconnect.
- On old Pages Router, each time navigate = full remount = lost WebSocket = flicker.

### 1.4. Suspense & Streaming — Progressive Loading

```tsx
// app/(dashboard)/page.tsx — Server Component
import { Suspense } from "react";
import { PriceBoard } from "./_components/price-board";
import { TradingChart } from "./_components/trading-chart";
import { AgentInsights } from "./_components/agent-insights";

export default function DashboardPage() {
  return (
    <div className="grid h-full grid-cols-[1fr_400px] grid-rows-[60%_40%] gap-1">
      {/* Chart streams first — highest visual priority */}
      <Suspense fallback={<ChartSkeleton />}>
        <TradingChart />
      </Suspense>

      {/* Price board streams second */}
      <Suspense fallback={<GridSkeleton />}>
        <PriceBoard />
      </Suspense>

      {/* AI Insights streams last — lowest priority, NPU may be slow */}
      <Suspense fallback={<InsightSkeleton />}>
        <AgentInsights />
      </Suspense>
    </div>
  );
}
```

#### Streaming Timeline

```
Browser request: GET /dashboard
                    │
Server response:    ▼
  ┌─────────────────────────────────────────────────────┐
  │ <html> <body> <Sidebar/> <TopNav/>                  │  ← Instant (RSC shell)
  │   <ChartSkeleton/>                                  │  ← Placeholder
  │   <GridSkeleton/>                                   │  ← Placeholder
  │   <InsightSkeleton/>                                │  ← Placeholder
  └─────────────────────────────────────────────────────┘
                    │  ~50ms
                    ▼
  ┌─────────────────────────────────────────────────────┐
  │   <TradingChart data={initialCandles}/>              │  ← Stream chunk 1
  └─────────────────────────────────────────────────────┘
                    │  ~80ms
                    ▼
  ┌─────────────────────────────────────────────────────┐
  │   <PriceBoard symbols={watchlist}/>                 │  ← Stream chunk 2
  └─────────────────────────────────────────────────────┘
                    │  ~200ms (NPU inference)
                    ▼
  ┌─────────────────────────────────────────────────────┐
  │   <AgentInsights analysis={aiResult}/>              │  ← Stream chunk 3
  └─────────────────────────────────────────────────────┘

Total Time to Interactive: ~80ms (chart visible)
Total Time to Complete: ~200ms (all widgets loaded)
```

**Benefits:** Users see the chart almost immediately. AI Insights (slowest due to NPU) does not block other widgets. Each `<Suspense>` boundary is an independent streaming unit.

---

## 2. AG GRID & RENDERING PERFORMANCE

### 2.1. Problem: Render 1,800 real-time stock codes

The Vietnamese market has ~1,800 codes (HOSE + HNX + UPCOM). Each code has ~15 data columns (price, volume, +/-, ceiling, floor, ...). Total: **~27,000 cells** updated continuously. If rendering naive:

```
1,800 rows × 15 cols = 27,000 DOM nodes
× 2-5 updates/second = 54,000-135,000 DOM mutations/second
→ Browser: 💀 (jank, dropped frames, unresponsive)
```

### 2.2. Solution 1: DOM Virtualization

AG Grid only renders rows **visible in the viewport**:

```
┌─────────────────────────────────────────┐
│ Viewport (visible area, ~30-40 rows)    │ ← Actual DOM nodes
├─────────────────────────────────────────┤
│                                         │
│  Row 1:  FPT   98.50  +1.2%  ...       │  ← Real <div>
│  Row 2:  VNM   72.00  -0.5%  ...       │  ← Real <div>
│  ...                                    │
│  Row 35: MWG   45.20  +0.8%  ...       │  ← Real <div>
│                                         │
├─────────────────────────────────────────┤
│ Off-screen (1,765 rows)                 │ ← NO DOM nodes
│ Represented by total scroll height only │    Just a tall empty <div>
└─────────────────────────────────────────┘

DOM nodes created: ~40 rows × 15 cols = 600 (instead of 27,000)
→ 97.8% reduction in DOM nodes
```

```tsx
// _components/price-board.tsx
"use client";

import { AgGridReact } from "ag-grid-react";
import { useRef, useCallback } from "react";
import type { GridApi, ColDef } from "ag-grid-community";

const columnDefs: ColDef[] = [
  { field: "symbol", pinned: "left", width: 80 },
  {
    field: "price",
    width: 90,
    cellRenderer: "agAnimateShowChangeCellRenderer",
    valueFormatter: ({ value }) => value?.toFixed(2),
  },
  {
    field: "change",
    width: 80,
    cellClassRules: {
      "text-emerald-400": (params) => params.value > 0,
      "text-rose-400": (params) => params.value < 0,
      "text-amber-400": (params) => params.value === 0,
    },
  },
  { field: "volume", width: 100, valueFormatter: formatVolume },
  { field: "ceiling", width: 80, cellClass: "text-fuchsia-400" },
  { field: "floor", width: 80, cellClass: "text-cyan-400" },
  // ... more columns
];

export function PriceBoard() {
  const gridRef = useRef<AgGridReact>(null);

  return (
    <div className="ag-theme-alpine-dark h-full w-full">
      <AgGridReact
        ref={gridRef}
        columnDefs={columnDefs}
        rowBuffer={10}              // Pre-render 10 rows above/below viewport
        rowModelType="clientSide"
        getRowId={(params) => params.data.symbol}
        animateRows={false}         // ★ Disable row animation for speed
        suppressCellFocus={true}    // ★ No focus ring overhead
        enableCellChangeFlash={true}// ★ Flash cell on value change
      />
    </div>
  );
}
```

### 2.3. Solution 2: Transaction-based Batch Updating

**Problem:** If you call `setRowData()` every time you receive 1 tick → React re-render the entire grid → jank.

**Solution:** AG Grid Transaction API updates **only cells change**, does not re-render the grid.

```tsx
// hooks/use-market-stream.ts
"use client";

import { useEffect, useRef } from "react";
import type { GridApi } from "ag-grid-community";
import { useMarketStore } from "@/stores/market-store";

/**
 * Batches incoming ticks and applies them to AG Grid
 * at screen refresh rate (60fps) via requestAnimationFrame.
 */
export function useMarketStream(gridApi: GridApi | null) {
  const pendingUpdates = useRef<Map<string, TickData>>(new Map());
  const rafId = useRef<number>(0);

  useEffect(() => {
    if (!gridApi) return;

    // Subscribe to WebSocket tick stream
    const unsubscribe = useMarketStore.subscribe(
      (state) => state.latestTick,
      (tick) => {
        if (!tick) return;
        // Accumulate updates — later ticks overwrite earlier ones for same symbol
        pendingUpdates.current.set(tick.symbol, tick);
      }
    );

    // Flush accumulated updates at 60fps
    function flushUpdates() {
      const updates = pendingUpdates.current;
      if (updates.size > 0) {
        // ★ Transaction update: AG Grid diffs internally,
        //   only touches changed cells in the DOM
        gridApi.applyTransactionAsync({
          update: Array.from(updates.values()),
        });
        updates.clear();
      }
      rafId.current = requestAnimationFrame(flushUpdates);
    }

    rafId.current = requestAnimationFrame(flushUpdates);

    return () => {
      unsubscribe();
      cancelAnimationFrame(rafId.current);
    };
  }, [gridApi]);
}
```

### 2.4. `requestAnimationFrame` — Why not use `setInterval`

```
setInterval(update, 16ms):
  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐
  │JS│  │JS│  │JS│  │JS│  │JS│  │JS│   ← JS execution
  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘
    ▼     ▼     ▼     ▼     ▼     ▼
  ┌──┐       ┌──┐       ┌──┐            ← Actual frames (browser may skip)
  │ F1│      │ F2│      │ F3│
  └──┘       └──┘       └──┘
  Problem: JS runs even when browser can't paint → wasted CPU, potential jank

requestAnimationFrame(update):
  ┌──┐       ┌──┐       ┌──┐
  │JS│       │JS│       │JS│            ← JS runs ONLY before paint
  └──┘       └──┘       └──┘
    ▼          ▼          ▼
  ┌──┐       ┌──┐       ┌──┐
  │ F1│      │ F2│      │ F3│            ← Every JS run = 1 frame painted
  └──┘       └──┘       └──┘
  Benefit: Zero wasted work. Automatically throttles on background tabs.
```

**Combined with batching:**
- Between 2 frames (~16.6ms at 60fps), can receive 50-200 ticks via WebSocket.
- All are accumulated into `pendingUpdates` Map (latest-wins per symbol).
- `requestAnimationFrame` callback flush **1 time** → AG Grid `applyTransactionAsync` diff **1 time** → Browser paint **1 time**.
- Result: **1 DOM update per frame**, regardless of the number of ticks.

### 2.5. Performance Budget

| Metric | Target | Technique |
|:---|:---|:---|
| DOM nodes (grid) | < 800 | Virtualization (viewport rows only) |
| DOM mutations/frame | < 50 cells | Transaction batch + rAF |
| JS execution/frame | < 8ms | Offload sort/filter to AG Grid internal worker |
| Frame rate | ≥ 55fps sustained | No layout thrashing, CSS containment |
| Memory (1,800 rows) | < 15MB | Flat row data objects, no nested React state |

---

## 3. CANVAS vs SVG — CHARTING ENGINE ANALYSIS

### 3.1. Rendering Pipeline Comparison

```
SVG Pipeline (D3.js, Recharts):
  Data Change
    → Create/Update SVG DOM elements (<rect>, <line>, <path>)
    → Browser Style Calculation (CSS on each element)
    → Layout (reflow — position each element)
    → Paint (rasterize each element separately)
    → Composite

  Each candlestick = 1 <rect> (body) + 1 <line> (wick) = 2 DOM nodes
  500 candles = 1,000 SVG DOM nodes + event listeners

Canvas Pipeline (TradingView Lightweight Charts):
  Data Change
    → JavaScript draws directly to bitmap buffer (ctx.fillRect, ctx.lineTo)
    → Browser composites single <canvas> layer
    → Done

  Each candlestick = 2 draw calls (fillRect + lineTo) — NO DOM nodes
  500 candles = 1 <canvas> element, ~1,000 draw calls to pixel buffer
```

### 3.2. Benchmark: 500 Candles + 3 Indicators + Real-time Updates

| Metric | SVG (D3.js/Recharts) | Canvas (TradingView LW) | Ratio |
|:---|:---|:---|:---|
| **DOM nodes** | ~2,500 (candles + indicators + axes) | **3** (canvas + 2 overlays) | **833x fewer** |
| **Initial render** | ~120-200ms (DOM creation + layout) | ~15-30ms (draw calls) | **5-8x faster** |
| **Update 1 candle** | ~8-15ms (DOM diff + reflow) | ~1-3ms (redraw dirty region) | **5x faster** |
| **Memory** | ~8-12MB (DOM tree + event listeners) | ~2-3MB (pixel buffer) | **4x less** |
| **Scroll/Zoom** | Reflow all elements → jank | Redraw bitmap → smooth | **No contest** |
| **10,000 candles** | Unusable (>5s render, scroll freezes) | Smooth (~50ms render) | **∞** |

### 3.3. Why SVG is still good for some use cases (but not trading)

| Use case | SVG ✅ | Canvas ✅ |
|:---|:---|:---|
| Dashboard pie/bar charts (< 100 elements) |Good — CSS styling, accessibility| Overkill |
| Interactive tooltips, hover effects | Native DOM events |Must implement hit-testing yourself|
| Print/Export to PDF | Vector — sharp at any resolution | Rasterized — fixed resolution |
| **Real-time candlestick (500+ candles, 2-5 updates/s)** |❌ Not feasible|✅ **Only feasible**|
| **Tick chart (thousands of points/minute)** | ❌ DOM explosion | ✅ **Trivial** |

### 3.4. TradingView Lightweight Charts — Integration Pattern

```tsx
// _components/trading-chart.tsx
"use client";

import { useEffect, useRef } from "react";
import { createChart, type IChartApi, type ISeriesApi } from "lightweight-charts";
import { useMarketStore } from "@/stores/market-store";

export function TradingChart({ symbol }: { symbol: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  // Initialize chart ONCE
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: "#09090b" },   // zinc-950
        textColor: "#a1a1aa",                // zinc-400
      },
      grid: {
        vertLines: { color: "#27272a33" },   // zinc-800 translucent
        horzLines: { color: "#27272a33" },
      },
      crosshair: { mode: 0 },               // Normal crosshair
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        borderColor: "#27272a",
      },
      rightPriceScale: { borderColor: "#27272a" },
    });

    const series = chart.addCandlestickSeries({
      upColor: "#34d399",        // emerald-400
      downColor: "#f87171",      // rose-400
      borderVisible: false,
      wickUpColor: "#34d399",
      wickDownColor: "#f87171",
    });

    chartRef.current = chart;
    seriesRef.current = series;

    // Responsive resize
    const observer = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      chart.applyOptions({ width, height });
    });
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chart.remove();
    };
  }, []);

  // Subscribe to real-time candle updates
  useEffect(() => {
    const unsubscribe = useMarketStore.subscribe(
      (state) => state.candles[symbol],
      (candle) => {
        if (candle && seriesRef.current) {
          // ★ update() is O(1) — modifies last candle or appends new one
          // No DOM manipulation. Just pixel buffer redraw.
          seriesRef.current.update(candle);
        }
      }
    );
    return unsubscribe;
  }, [symbol]);

  return <div ref={containerRef} className="h-full w-full" />;
}
```

### 3.5. Custom Overlays — Agent Markers on Chart

```tsx
// _components/chart-overlays/signal-markers.ts
import type { ISeriesApi, SeriesMarker, Time } from "lightweight-charts";

interface AgentSignal {
  time: Time;
  type: "BUY" | "SELL";
  reason: string;
  score: number;
}

/**
 * Renders buy/sell markers from Technical Agent signals.
 * Zero DOM nodes — drawn directly on canvas by the chart library.
 */
export function applySignalMarkers(
  series: ISeriesApi<"Candlestick">,
  signals: AgentSignal[]
): void {
  const markers: SeriesMarker<Time>[] = signals.map((s) => ({
    time: s.time,
    position: s.type === "BUY" ? "belowBar" : "aboveBar",
    color: s.type === "BUY" ? "#34d399" : "#f87171",
    shape: s.type === "BUY" ? "arrowUp" : "arrowDown",
    text: `${s.type} (${s.score.toFixed(1)}) — ${s.reason}`,
  }));

  series.setMarkers(markers);
}
```

---

## 4. STATE MANAGEMENT

### 4.1. Why NOT use React Context for real-time data

```tsx
// ❌ ANTI-PATTERN: Context for high-frequency data

const MarketContext = createContext<MarketState>(initialState);

function MarketProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<MarketState>(initialState);

  useEffect(() => {
    ws.onmessage = (msg) => {
      setState((prev) => ({ ...prev, ticks: [...prev.ticks, msg.data] }));
      // ★ PROBLEM: Every setState triggers re-render of ALL consumers
      // Even components that only care about 1 symbol re-render on EVERY tick
    };
  }, []);

  return (
    <MarketContext.Provider value={state}>
      {children}
      {/* ★ ALL children re-render on every tick — catastrophic */}
    </MarketContext.Provider>
  );
}
```

**Core issue:** Context API does not support **selector-based subscription**. When the value changes, **every** component that uses `useContext(MarketContext)` re-renders, regardless of whether that component uses the changed data or not.

At 200 ticks/sec → 200 re-renders/sec for **each** consumer component → UI freeze.

### 4.2. Zustand — Selector-based, Minimal Re-renders

```tsx
// stores/market-store.ts
import { create } from "zustand";
import { subscribeWithSelector } from "zustand/middleware";

interface TickData {
  symbol: string;
  price: number;
  change: number;
  volume: number;
  timestamp: number;
}

interface CandleData {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
}

interface MarketState {
  // Tick data indexed by symbol for O(1) lookup
  ticks: Record<string, TickData>;
  // Candle data indexed by symbol
  candles: Record<string, CandleData>;
  // Latest tick (for global subscribers like DataAgent status)
  latestTick: TickData | null;

  // Actions
  updateTick: (tick: TickData) => void;
  updateCandle: (symbol: string, candle: CandleData) => void;
  bulkUpdateTicks: (ticks: TickData[]) => void;
}

export const useMarketStore = create<MarketState>()(
  subscribeWithSelector((set) => ({
    ticks: {},
    candles: {},
    latestTick: null,

    updateTick: (tick) =>
      set((state) => ({
        latestTick: tick,
        ticks: { ...state.ticks, [tick.symbol]: tick },
      })),

    updateCandle: (symbol, candle) =>
      set((state) => ({
        candles: { ...state.candles, [symbol]: candle },
      })),

    bulkUpdateTicks: (ticks) =>
      set((state) => {
        const updated = { ...state.ticks };
        for (const tick of ticks) {
          updated[tick.symbol] = tick;
        }
        return { ticks: updated, latestTick: ticks[ticks.length - 1] };
      }),
  }))
);
```

### 4.3. Selector Pattern — Surgical Re-renders

```tsx
// ★ Component ONLY re-renders when FPT price changes
// Do not re-render when VNM, MWG, or any other symbol changes

function FPTPrice() {
  const price = useMarketStore((state) => state.ticks["FPT"]?.price);
  //                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
// Selector: Zustand compares with Object.is()
// Only re-render when return value changes
  return <span>{price?.toFixed(2) ?? "—"}</span>;
}

Error 500 (Server Error)!!1500.That’s an error.There was an error. Please try again later.That’s all we know.
function AllTicksGrid() {
  const ticks = useMarketStore((state) => state.ticks);
// Ticks object reference changes every update → re-render
// But AG Grid Transaction API handles diff internally (Section 2.3)
  return <AgGridReact rowData={Object.values(ticks)} />;
}
```

### 4.4. Store Architecture — Separation by domain

```
stores/
├── market-store.ts        # Ticks, candles, market status
│                          # Update frequency: 100-500/s
│                          # Subscribers: PriceBoard, TradingChart
│
├── portfolio-store.ts     # Positions, cash, PnL
│                          # Update frequency: 1-5/s
│                          # Subscribers: PortfolioDashboard, OrderForm
│
├── signal-store.ts        # Agent signals, AI insights, scores
│                          # Update frequency: 0.1-1/s
│                          # Subscribers: SignalPanel, ChartOverlays
│
├── order-store.ts         # Open orders, order history
│                          # Update frequency: on-demand
│                          # Subscribers: OrderBook, OrderHistory
│
└── ui-store.ts            # UI state: active symbol, layout, theme
                           # Update frequency: user-driven
                           # Subscribers: everywhere (but rarely changes)
```

**Why split the store?**
- `market-store` changes 100-500 times/second. If combined with `ui-store`, each tick will trigger re-render for **all** UI components (theme toggle, layout panels, ...).
- Separate store = separate subscription scope = **only related components can re-render**.

### 4.5. WebSocket → Store Bridge

```tsx
// providers/ws-provider.tsx
"use client";

import { useEffect, useRef } from "react";
import { useMarketStore } from "@/stores/market-store";
import { useSignalStore } from "@/stores/signal-store";
import { usePortfolioStore } from "@/stores/portfolio-store";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws";

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    function connect() {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);

        // Route message to correct store based on type
        switch (msg.type) {
          case "tick":
            useMarketStore.getState().updateTick(msg.payload);
            break;
          case "tick_batch":
            useMarketStore.getState().bulkUpdateTicks(msg.payload);
            break;
          case "candle":
            useMarketStore.getState().updateCandle(
              msg.payload.symbol,
              msg.payload.candle
            );
            break;
          case "signal":
            useSignalStore.getState().addSignal(msg.payload);
            break;
          case "portfolio":
            usePortfolioStore.getState().sync(msg.payload);
            break;
        }
      };

      ws.onclose = () => {
        // Exponential backoff reconnect
        reconnectTimer.current = setTimeout(connect, 2000);
      };

      ws.onerror = () => ws.close();
    }

    connect();

    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, []);

  return <>{children}</>;
}
```

**Architectural note:**
- `WebSocketProvider` is the only Client Component at the root level.
- Call `getState()` instead of hook → **does not trigger React re-render** in provider. Store subscribers automatically re-render when the selector value changes.
- Message routing using `switch` — O(1), no need for complicated event emitters.

### 4.6. Context API — When is it still available?

| Data type | Update frequency | Solution |
|:---|:---|:---|
| Theme (dark/light) | ~0/s (user toggle) |Context ✅ or Zustand|
| User session / auth | ~0/s (login/logout) | Context ✅ |
| Active symbol selection | ~0.1/s (user click) | Zustand (shared across widgets) |
| Market ticks | 100-500/s | Zustand ✅ — Context ❌ |
| Agent signals | 0.1-1/s | Zustand ✅ — Context ❌ |

**Rule of thumb:** If data changes > 1 time/second → **Zustand**. If data is almost static → Context OK.

---

## 5. COMPONENT TESTING

### 5.1. Testing Stack

| Tool | Role | Scope |
|:---|:---|:---|
| **Vitest** | Test runner (Vite-native, ESM) | Unit + integration tests |
| **React Testing Library (RTL)** | Component behavior testing | User interaction, DOM assertions |
| **MSW (Mock Service Worker)** | API/WebSocket mocking | Network-level mocks |
| **Storybook 8** | Visual component development | Isolated UI, visual regression |
| **Playwright** | E2E testing | Full browser, critical paths |

### 5.2. Testing Pyramid

```
                    ┌───────┐
                    │  E2E  │  ~5 tests
                    │Playwright│  Critical flows: login → view chart → place order
                    ├───────┤
                ┌───┴───────┴───┐
                │  Integration  │  ~20 tests
                │  RTL + MSW    │  Widget behavior with mocked WebSocket
                ├───────────────┤
            ┌───┴───────────────┴───┐
            │      Unit Tests       │  ~50+ tests
            │  Vitest + RTL         │  Pure components, hooks, store logic
            ├───────────────────────┤
        ┌───┴───────────────────────┴───┐
        │        Storybook Stories       │  ~30+ stories
        │  Visual catalog + a11y checks  │  Every reusable component
        └───────────────────────────────┘
```

### 5.3. Unit Test — Zustand Store

```tsx
// __tests__/stores/market-store.test.ts
import { describe, it, expect, beforeEach } from "vitest";
import { useMarketStore } from "@/stores/market-store";

describe("MarketStore", () => {
  beforeEach(() => {
    // Reset store between tests
    useMarketStore.setState({
      ticks: {},
      candles: {},
      latestTick: null,
    });
  });

  it("updates single tick by symbol", () => {
    const tick = {
      symbol: "FPT",
      price: 98.5,
      change: 1.2,
      volume: 50000,
      timestamp: Date.now(),
    };

    useMarketStore.getState().updateTick(tick);

    const state = useMarketStore.getState();
    expect(state.ticks["FPT"]).toEqual(tick);
    expect(state.latestTick).toEqual(tick);
  });

  it("bulk update overwrites existing ticks", () => {
    const ticks = [
      { symbol: "FPT", price: 98.5, change: 1.2, volume: 50000, timestamp: 1 },
      { symbol: "VNM", price: 72.0, change: -0.5, volume: 30000, timestamp: 2 },
      { symbol: "FPT", price: 99.0, change: 1.7, volume: 60000, timestamp: 3 },
    ];

    useMarketStore.getState().bulkUpdateTicks(ticks);

    const state = useMarketStore.getState();
    expect(state.ticks["FPT"]?.price).toBe(99.0); // Last FPT wins
    expect(state.ticks["VNM"]?.price).toBe(72.0);
    expect(state.latestTick?.symbol).toBe("FPT"); // Last in array
  });

  it("does not mutate previous state reference", () => {
    const before = useMarketStore.getState().ticks;

    useMarketStore.getState().updateTick({
      symbol: "MWG",
      price: 45.2,
      change: 0.8,
      volume: 20000,
      timestamp: Date.now(),
    });

    const after = useMarketStore.getState().ticks;
    expect(before).not.toBe(after); // New reference = immutable update
  });
});
```

### 5.4. Component Test — RTL + Mocked Store

```tsx
// __tests__/components/price-cell.test.tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PriceCell } from "@/components/price-cell";

describe("PriceCell", () => {
  it("renders price with 2 decimal places", () => {
    render(<PriceCell value={98.5} />);
    expect(screen.getByText("98.50")).toBeInTheDocument();
  });

  it("applies green class for positive change", () => {
    render(<PriceCell value={98.5} change={1.2} />);
    const el = screen.getByText("98.50");
    expect(el).toHaveClass("text-emerald-400");
  });

  it("applies red class for negative change", () => {
    render(<PriceCell value={72.0} change={-0.5} />);
    const el = screen.getByText("72.00");
    expect(el).toHaveClass("text-rose-400");
  });

  it("applies yellow class for ceiling price", () => {
    render(<PriceCell value={105.4} isCeiling />);
    const el = screen.getByText("105.40");
    expect(el).toHaveClass("text-fuchsia-400");
  });

  it("renders dash for null value", () => {
    render(<PriceCell value={null} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
```

### 5.5. Integration Test — WebSocket Widget

```tsx
// __tests__/integration/price-board.test.tsx
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { PriceBoard } from "@/app/(dashboard)/_components/price-board";
import { useMarketStore } from "@/stores/market-store";

// Mock AG Grid to avoid heavy enterprise dependency in tests
vi.mock("ag-grid-react", () => ({
  AgGridReact: ({ rowData }: { rowData: unknown[] }) => (
    <div data-testid="mock-grid">
      {(rowData ?? []).map((row: any) => (
        <div key={row.symbol} data-testid={`row-${row.symbol}`}>
          {row.symbol}: {row.price}
        </div>
      ))}
    </div>
  ),
}));

describe("PriceBoard Integration", () => {
  beforeEach(() => {
    useMarketStore.setState({ ticks: {}, candles: {}, latestTick: null });
  });

  it("displays ticks from store", async () => {
    // Simulate tick arriving via WebSocket
    useMarketStore.getState().updateTick({
      symbol: "FPT",
      price: 98.5,
      change: 1.2,
      volume: 50000,
      timestamp: Date.now(),
    });

    render(<PriceBoard />);

    await waitFor(() => {
      expect(screen.getByTestId("row-FPT")).toHaveTextContent("FPT: 98.5");
    });
  });
});
```

### 5.6. Storybook — Component Catalog

```tsx
// components/price-cell.stories.tsx
import type { Meta, StoryObj } from "@storybook/react";
import { PriceCell } from "./price-cell";

const meta: Meta<typeof PriceCell> = {
  title: "Trading/PriceCell",
  component: PriceCell,
  tags: ["autodocs"],
  argTypes: {
    value: { control: "number" },
    change: { control: "number" },
    isCeiling: { control: "boolean" },
    isFloor: { control: "boolean" },
  },
  decorators: [
    (Story) => (
      <div className="bg-zinc-950 p-4 font-mono">
        <Story />
      </div>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof PriceCell>;

export const Default: Story = {
  args: { value: 98.5, change: 0 },
};

export const Positive: Story = {
  args: { value: 98.5, change: 1.2 },
};

export const Negative: Story = {
  args: { value: 72.0, change: -0.5 },
};

export const Ceiling: Story = {
  args: { value: 105.4, isCeiling: true },
};

export const Floor: Story = {
  args: { value: 86.8, isFloor: true },
};

export const Null: Story = {
  args: { value: null },
};
```

### 5.7. Testing Conventions

```
★ RULE: Test BEHAVIOR, not implementation.
  ✅ "displays price with 2 decimal places"
  ❌ "calls setState with correct value"

★ RULE: No snapshot tests for dynamic components.
  Snapshot tests break on every style change → noise, not signal.

★ RULE: Mock at the boundary, not inside.
  ✅ Mock WebSocket connection (MSW)
  ✅ Mock AG Grid (heavy enterprise dep)
  ❌ Mock internal hooks or Zustand internals

★ RULE: Every Storybook story = implicit visual test.
  Use Chromatic or Percy for visual regression CI.

★ RULE: Test file co-location.
  __tests__/ mirrors src/ structure.
  Stories live next to components: price-cell.tsx + price-cell.stories.tsx
```

### 5.8. Test Execution

```bash
# Unit + Integration tests
pnpm vitest run

# Watch mode (development)
pnpm vitest

# Coverage
pnpm vitest run --coverage --coverage.thresholds.lines=80

# Storybook
pnpm storybook dev -p 6006

# Storybook build (CI)
pnpm storybook build

# E2E (Playwright)
pnpm playwright test

# Type check
pnpm tsc --noEmit
```

---

## APPENDIX A: PERFORMANCE CHECKLIST

```
Pre-launch checklist for rendering performance:

□ AG Grid: rowBuffer ≤ 10, animateRows = false
□ AG Grid: getRowId returns stable key (symbol)
□ AG Grid: applyTransactionAsync (not setRowData) for updates
□ Chart: Canvas-based (not SVG)
□ Chart: ResizeObserver (not window.onresize)
□ WebSocket: Messages routed via store.getState() (not setState in provider)
□ Zustand: Selectors return minimal data (not entire state)
□ Zustand: Separate stores for different update frequencies
□ React: No unnecessary "use client" on static components
□ React: Suspense boundaries around async widgets
□ CSS: contain: layout style paint on grid/chart containers
□ Bundle: AG Grid + Chart lazy-loaded (dynamic import)
□ Bundle: No moment.js (use date-fns or Temporal)
□ Images: Next.js <Image> with priority for above-fold
```

## APPENDIX B: BUNDLE SIZE BUDGET

| Package | Budget | Actual (est.) | Notes |
|:---|:---|:---|:---|
| React + React DOM | ~45 KB | ~44 KB | Non-negotiable |
| Next.js runtime | ~90 KB | ~85 KB | App Router overhead |
| AG Grid Enterprise | ~200 KB | ~180 KB | Tree-shaken, only used modules |
| TradingView LW Charts | ~45 KB | ~42 KB | Lightweight by design |
| Zustand | ~2 KB | ~1.5 KB | Minimal |
| Tailwind CSS (purged) | ~15 KB | ~12 KB | Only used classes |
| Shadcn UI components | ~30 KB | ~25 KB | Only imported components |
| **Total (gzipped)** | **< 450 KB** | **~390 KB** | Target: < 500 KB |

---

*Document authored by Senior Frontend Engineer. All code samples target Next.js 15 + React 19 + TypeScript strict mode.*
