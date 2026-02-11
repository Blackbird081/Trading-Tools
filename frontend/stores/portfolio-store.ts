import { create } from "zustand";
import { subscribeWithSelector } from "zustand/middleware";
import type { Position } from "@/types/market";

interface PortfolioState {
  positions: Position[];
  cash: number;
  nav: number;
  purchasingPower: number;

  sync: (data: {
    positions: Position[];
    cash: number;
    nav: number;
    purchasingPower: number;
  }) => void;
  updatePosition: (position: Position) => void;
}

export const usePortfolioStore = create<PortfolioState>()(
  subscribeWithSelector((set) => ({
    positions: [],
    cash: 0,
    nav: 0,
    purchasingPower: 0,

    sync: (data) => set(data),

    updatePosition: (position) =>
      set((state) => ({
        positions: state.positions.map((p) =>
          p.symbol === position.symbol ? position : p
        ),
      })),
  }))
);
