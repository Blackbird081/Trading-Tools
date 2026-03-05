import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import MarketBoardPage from "@/app/market-board/page";
import { useUIStore } from "@/stores/ui-store";
import { useMarketStore } from "@/stores/market-store";

const { mockBuildMarketSectors } = vi.hoisted(() => ({
  mockBuildMarketSectors: vi.fn(),
}));

vi.mock("@/lib/market-sectors", () => ({
  buildMarketSectors: mockBuildMarketSectors,
}));

vi.mock("@/components/sector-column", () => ({
  SectorColumn: ({ title }: { title: string }) => <div data-testid="sector-column">{title}</div>,
}));

vi.mock("@/components/market-index-bar", () => ({
  MarketIndexBar: () => <div data-testid="market-index-bar">index-bar</div>,
}));

vi.mock("@/components/error-boundary", () => ({
  TradingErrorBoundary: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

describe("MarketBoard mobile controls", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();

    useUIStore.setState({
      activeSymbol: "FPT",
      commandPaletteOpen: false,
      sidebarCollapsed: false,
      preset: "TOP100",
      years: 3,
      symbolPopupOpen: false,
      symbolPopupSymbol: null,
    });
    useMarketStore.setState({
      ticks: {},
      candles: {},
      latestTick: null,
      connectionStatus: "disconnected",
    });

    mockBuildMarketSectors.mockReturnValue([
      { title: "VN30", symbols: ["AAA"] },
      { title: "Bất động sản", symbols: ["BBB"] },
      { title: "Chứng khoán", symbols: ["CCC"] },
      { title: "Ngân hàng", symbols: ["DDD"] },
    ]);
  });

  it("renders consistent mobile sector tab size and allows selection", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ ticks: [] }),
      } as Response),
    );

    render(<MarketBoardPage />);
    await waitFor(() => expect(screen.getByTestId("market-index-bar")).toBeInTheDocument());

    const vn30Tab = screen.getByRole("button", { name: "VN30" });
    const bdsTab = screen.getByRole("button", { name: "Bất động sản" });
    const ckTab = screen.getByRole("button", { name: "Chứng khoán" });
    const bankTab = screen.getByRole("button", { name: "Ngân hàng" });
    const tabs = [vn30Tab, bdsTab, ckTab, bankTab];

    tabs.forEach((tab) => {
      expect(tab.className).toContain("h-14");
      expect(tab.className).toContain("rounded-md");
    });

    fireEvent.click(ckTab);
    expect(ckTab.className).toContain("bg-emerald-600");
    expect(vn30Tab.className).toContain("bg-zinc-800");
  });

  it("supports desktop page switch controls for sector paging", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ ticks: [] }),
      } as Response),
    );

    render(<MarketBoardPage />);
    await waitFor(() => expect(screen.getByRole("button", { name: /Trang 2/i })).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /Trang 2/i }));
    expect(screen.getByText("2 / 2")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Trước/i }));
    expect(screen.getByText("1 / 2")).toBeInTheDocument();
  });

  it("falls back to mock ticks and supports mobile swipe navigation", async () => {
    const replaceTicksSpy = vi.fn();
    useMarketStore.setState({ replaceTicks: replaceTicksSpy } as Partial<ReturnType<typeof useMarketStore.getState>>);

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ ticks: [] }),
      } as Response),
    );

    const { container } = render(<MarketBoardPage />);
    await waitFor(() => expect(replaceTicksSpy).toHaveBeenCalled());

    const swipeContainer = Array.from(container.querySelectorAll("div")).find(
      (el) => el.className.includes("md:hidden") && el.className.includes("shrink-0"),
    );
    expect(swipeContainer).toBeTruthy();

    const firstTab = screen.getByRole("button", { name: "VN30" });
    const secondTab = screen.getByRole("button", { name: "Bất động sản" });
    expect(firstTab.className).toContain("bg-emerald-600");

    fireEvent.touchStart(swipeContainer as Element, {
      touches: [{ clientX: 220, clientY: 100 }],
    });
    fireEvent.touchEnd(swipeContainer as Element, {
      changedTouches: [{ clientX: 140, clientY: 102 }],
    });

    expect(secondTab.className).toContain("bg-emerald-600");
  });
});
