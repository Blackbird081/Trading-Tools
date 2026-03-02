import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { DataLoader } from "@/app/(dashboard)/_components/data-loader";
import { useMarketStore } from "@/stores/market-store";
import { useUIStore } from "@/stores/ui-store";

function mockCachedEmptyResponse(): Response {
  return {
    ok: true,
    json: async () => ({
      ticks: [],
      symbol_count: 0,
      years: 3,
      last_updated: null,
    }),
  } as Response;
}

function mockEmptyStreamResponse(): Response {
  return {
    ok: true,
    body: {
      getReader: () => ({
        read: vi.fn().mockResolvedValue({ done: true, value: undefined }),
      }),
    } as unknown as ReadableStream<Uint8Array>,
  } as Response;
}

describe("DataLoader (P0 gate)", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();

    useMarketStore.setState({
      ticks: {},
      candles: {},
      latestTick: null,
      connectionStatus: "disconnected",
    });

    useUIStore.setState({
      activeSymbol: "FPT",
      commandPaletteOpen: false,
      sidebarCollapsed: false,
      preset: "VN30",
      years: 3,
      symbolPopupOpen: false,
      symbolPopupSymbol: null,
    });
  });

  it("does not auto-run load/update on mount", async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockCachedEmptyResponse());
    vi.stubGlobal("fetch", fetchMock);

    render(<DataLoader />);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const firstCallUrl = String(fetchMock.mock.calls[0]?.[0] ?? "");
    expect(firstCallUrl).toContain("/cached-data?preset=VN30");

    const calledUrls = fetchMock.mock.calls.map((call) => String(call[0]));
    expect(calledUrls.some((url) => url.includes("/load-data"))).toBe(false);
    expect(calledUrls.some((url) => url.includes("/update-data"))).toBe(false);
  });

  it("runs load only after user clicks Load button", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(mockCachedEmptyResponse())
      .mockResolvedValueOnce(mockEmptyStreamResponse());
    vi.stubGlobal("fetch", fetchMock);

    render(<DataLoader />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    const loadButton = await screen.findByRole("button", { name: /^load$/i });
    fireEvent.click(loadButton);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    const secondCallUrl = String(fetchMock.mock.calls[1]?.[0] ?? "");
    expect(secondCallUrl).toContain("/load-data?preset=VN30&years=3");
  });
});
