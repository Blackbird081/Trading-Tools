import { describe, it, expect, beforeEach } from "vitest";
import { useUIStore } from "@/stores/ui-store";

describe("UIStore", () => {
  beforeEach(() => {
    useUIStore.setState({
      activeSymbol: "FPT",
      commandPaletteOpen: false,
      sidebarCollapsed: false,
    });
  });

  it("sets active symbol", () => {
    useUIStore.getState().setActiveSymbol("VNM");
    expect(useUIStore.getState().activeSymbol).toBe("VNM");
  });

  it("toggles command palette", () => {
    expect(useUIStore.getState().commandPaletteOpen).toBe(false);
    useUIStore.getState().toggleCommandPalette();
    expect(useUIStore.getState().commandPaletteOpen).toBe(true);
    useUIStore.getState().toggleCommandPalette();
    expect(useUIStore.getState().commandPaletteOpen).toBe(false);
  });

  it("toggles sidebar", () => {
    expect(useUIStore.getState().sidebarCollapsed).toBe(false);
    useUIStore.getState().toggleSidebar();
    expect(useUIStore.getState().sidebarCollapsed).toBe(true);
  });
});
