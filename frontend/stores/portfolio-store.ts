import { create } from "zustand";
import { subscribeWithSelector } from "zustand/middleware";
import type { Position } from "@/types/market";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

interface PortfolioState {
  positions: Position[];
  cash: number;
  nav: number;
  purchasingPower: number;
  realizedPnl: number;
  unrealizedPnl: number;
  lastSyncAt: string | null;
  pnlSeries: Array<{ date: string; pnl: number; nav: number }>;
  loading: boolean;
  error: string | null;

  sync: (data: {
    positions: Position[];
    cash: number;
    nav: number;
    purchasingPower: number;
    realizedPnl?: number;
    unrealizedPnl?: number;
    lastSyncAt?: string | null;
  }) => void;
  fetchPortfolio: () => Promise<void>;
  refreshPortfolio: () => Promise<void>;
  fetchPnlSeries: (days?: number) => Promise<void>;
  updatePosition: (position: Position) => void;
}

export const usePortfolioStore = create<PortfolioState>()(
  subscribeWithSelector((set) => ({
    positions: [],
    cash: 0,
    nav: 0,
    purchasingPower: 0,
    realizedPnl: 0,
    unrealizedPnl: 0,
    lastSyncAt: null,
    pnlSeries: [],
    loading: false,
    error: null,

    sync: (data) =>
      set({
        positions: data.positions,
        cash: data.cash,
        nav: data.nav,
        purchasingPower: data.purchasingPower,
        realizedPnl: data.realizedPnl ?? 0,
        unrealizedPnl: data.unrealizedPnl ?? 0,
        lastSyncAt: data.lastSyncAt ?? null,
      }),

    fetchPortfolio: async () => {
      set({ loading: true, error: null });
      try {
        const [summaryRes, positionsRes] = await Promise.all([
          fetch(`${API_BASE}/portfolio`),
          fetch(`${API_BASE}/portfolio/positions`),
        ]);
        if (!summaryRes.ok || !positionsRes.ok) throw new Error("Portfolio API failed");
        const summary = (await summaryRes.json()) as Record<string, unknown>;
        const posData = (await positionsRes.json()) as { positions?: Array<Record<string, unknown>> };
        const positions = (posData.positions ?? []).map((p) => {
          const avgPrice = Number(p.avg_price ?? 0);
          const marketPrice = Number(p.market_price ?? 0);
          const quantity = Number(p.quantity ?? 0);
          const pnl = Number(p.unrealized_pnl ?? (marketPrice - avgPrice) * quantity);
          const pnlPct = Number(
            p.unrealized_pnl_pct ?? (avgPrice > 0 ? ((marketPrice - avgPrice) / avgPrice) * 100 : 0),
          );
          return {
            symbol: String(p.symbol ?? ""),
            quantity,
            sellableQty: Number(p.sellable_qty ?? quantity),
            avgPrice,
            marketPrice,
            pnl,
            pnlPct,
          };
        });

        set({
          positions,
          cash: Number(summary.cash ?? 0),
          nav: Number(summary.nav ?? 0),
          purchasingPower: Number(summary.purchasing_power ?? 0),
          realizedPnl: Number(summary.realized_pnl ?? 0),
          unrealizedPnl: Number(summary.unrealized_pnl ?? 0),
          lastSyncAt: String(summary.last_sync_at ?? ""),
          loading: false,
          error: null,
        });
      } catch (err) {
        set({ loading: false, error: err instanceof Error ? err.message : "Cannot fetch portfolio" });
      }
    },

    refreshPortfolio: async () => {
      set({ loading: true, error: null });
      try {
        const res = await fetch(`${API_BASE}/portfolio/refresh`, { method: "POST" });
        if (!res.ok) throw new Error("Refresh API failed");
        await fetch(`${API_BASE}/portfolio/reconcile`, { method: "POST" });
        await (async () => {
          const state = usePortfolioStore.getState();
          await state.fetchPortfolio();
        })();
      } catch (err) {
        set({ loading: false, error: err instanceof Error ? err.message : "Cannot refresh portfolio" });
      }
    },

    fetchPnlSeries: async (days = 30) => {
      try {
        const res = await fetch(`${API_BASE}/portfolio/pnl?days=${days}`);
        if (!res.ok) throw new Error("Pnl API failed");
        const data = (await res.json()) as { series?: Array<{ date: string; pnl: number; nav: number }> };
        set({ pnlSeries: data.series ?? [] });
      } catch (err) {
        set({ error: err instanceof Error ? err.message : "Cannot fetch pnl series" });
      }
    },

    updatePosition: (position) =>
      set((state) => ({
        positions: state.positions.map((p) =>
          p.symbol === position.symbol ? position : p
        ),
      })),
  }))
);
