import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

type Preset = "VN30" | "TOP100";

interface UIState {
  activeSymbol: string;
  commandPaletteOpen: boolean;
  sidebarCollapsed: boolean;
  preset: Preset;
  years: number;
  // ★ NEW: Symbol popup state
  symbolPopupOpen: boolean;
  symbolPopupSymbol: string | null;

  setActiveSymbol: (symbol: string) => void;
  toggleCommandPalette: () => void;
  toggleSidebar: () => void;
  setPreset: (preset: Preset) => void;
  setYears: (years: number) => void;
  // ★ NEW: Symbol popup actions
  openSymbolPopup: (symbol: string) => void;
  closeSymbolPopup: () => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      activeSymbol: "FPT",
      commandPaletteOpen: false,
      sidebarCollapsed: false,
      preset: "VN30",
      years: 3,
      symbolPopupOpen: false,
      symbolPopupSymbol: null,

      setActiveSymbol: (symbol) => set({ activeSymbol: symbol }),
      toggleCommandPalette: () =>
        set((state) => ({ commandPaletteOpen: !state.commandPaletteOpen })),
      toggleSidebar: () =>
        set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setPreset: (preset) => set({ preset }),
      setYears: (years) => set({ years }),
      // ★ NEW: Symbol popup
      openSymbolPopup: (symbol) => set({ symbolPopupOpen: true, symbolPopupSymbol: symbol, activeSymbol: symbol }),
      closeSymbolPopup: () => set({ symbolPopupOpen: false }),
    }),
    {
      name: "algo-trading-ui",  // localStorage key
      storage: createJSONStorage(() => localStorage),
      // ★ Only persist user preferences, NOT transient UI state
      partialize: (state) => ({
        preset: state.preset,
        years: state.years,
        sidebarCollapsed: state.sidebarCollapsed,
        activeSymbol: state.activeSymbol,
      }),
    }
  )
);
