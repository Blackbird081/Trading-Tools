import { create } from "zustand";

type Preset = "VN30" | "TOP100";

interface UIState {
  activeSymbol: string;
  commandPaletteOpen: boolean;
  sidebarCollapsed: boolean;
  preset: Preset;
  years: number;

  setActiveSymbol: (symbol: string) => void;
  toggleCommandPalette: () => void;
  toggleSidebar: () => void;
  setPreset: (preset: Preset) => void;
  setYears: (years: number) => void;
}

export const useUIStore = create<UIState>()((set) => ({
  activeSymbol: "FPT",
  commandPaletteOpen: false,
  sidebarCollapsed: false,
  preset: "VN30",
  years: 3,

  setActiveSymbol: (symbol) => set({ activeSymbol: symbol }),
  toggleCommandPalette: () =>
    set((state) => ({ commandPaletteOpen: !state.commandPaletteOpen })),
  toggleSidebar: () =>
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  setPreset: (preset) => set({ preset }),
  setYears: (years) => set({ years }),
}));
