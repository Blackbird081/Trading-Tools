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

function mockCachedLoadedResponse(): Response {
  return {
    ok: true,
    json: async () => ({
      ticks: [
        {
          symbol: "FPT",
          price: 100,
          change: 1,
          changePct: 1,
          volume: 1000000,
          high: 101,
          low: 99,
          open: 99.5,
          ceiling: 107,
          floor: 93,
          reference: 99,
          timestamp: Date.now(),
        },
      ],
      symbol_count: 1,
      years: 3,
      last_updated: "02/03/2026 04:01",
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

function mockSseResponse(events: Array<{ event: string; data: Record<string, unknown> }>): Response {
  const payload = events
    .map((item) => `event: ${item.event}\ndata: ${JSON.stringify(item.data)}\n\n`)
    .join("");
  let done = false;
  return {
    ok: true,
    body: {
      getReader: () => ({
        read: vi.fn().mockImplementation(async () => {
          if (done) return { done: true, value: undefined };
          done = true;
          return { done: false, value: new TextEncoder().encode(payload) };
        }),
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
    await waitFor(() =>
      expect(screen.getByText("Data stream interrupted. Please retry Load/Update.")).toBeInTheDocument(),
    );
  });

  it("restores cache, enables update flow, and applies SSE tick/complete events", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(mockCachedLoadedResponse())
      .mockResolvedValueOnce(
        mockSseResponse([
          { event: "start", data: { total: 1, years: 3 } },
          { event: "progress", data: { loaded: 1, percent: 100, symbol: "FPT", status: "Updating..." } },
          {
            event: "tick",
            data: {
              symbol: "FPT",
              price: 123,
              change: 2,
              changePct: 1.5,
              volume: 1200000,
              high: 124,
              low: 122,
              open: 122.5,
              ceiling: 130,
              floor: 110,
              reference: 121,
              timestamp: 123456,
            },
          },
          { event: "complete", data: { loaded: 1, total: 1, message: "Update done", last_updated: "03/03/2026 09:10" } },
        ]),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<DataLoader />);

    await waitFor(() => expect(screen.getByText("1 symbols")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /market data/i }));

    const updateButton = await screen.findByRole("button", { name: /^update$/i });
    expect(updateButton).not.toBeDisabled();
    fireEvent.click(updateButton);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(String(fetchMock.mock.calls[1]?.[0] ?? "")).toContain("/update-data?preset=VN30");
    await waitFor(() => expect(screen.getByText("Update done")).toBeInTheDocument());
    expect(useMarketStore.getState().ticks.FPT?.price).toBe(123);
    expect(screen.getByText("Cập nhật: 03/03/2026 09:10")).toBeInTheDocument();
  });

  it("changes preset/years before load and passes them to load URL", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(mockCachedEmptyResponse())
      .mockResolvedValueOnce(mockCachedEmptyResponse())
      .mockResolvedValueOnce(mockEmptyStreamResponse());
    vi.stubGlobal("fetch", fetchMock);

    render(<DataLoader />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: "Top 100" }));
    const slider = screen.getByRole("slider");
    fireEvent.change(slider, { target: { value: "5" } });

    const loadButton = await screen.findByRole("button", { name: /^load$/i });
    fireEvent.click(loadButton);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    const calledUrls = fetchMock.mock.calls.map((call) => String(call[0] ?? ""));
    const hasLoadCall = calledUrls.some(
      (url) => url.includes("/load-data") && url.includes("preset=TOP100") && url.includes("years=5"),
    );
    expect(hasLoadCall, `Unexpected fetch urls: ${calledUrls.join(" | ")}`).toBe(true);
  });

  it("supports switching preset back to VN30 before load request", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(mockCachedEmptyResponse())
      .mockResolvedValueOnce(mockCachedEmptyResponse())
      .mockResolvedValueOnce(mockCachedEmptyResponse())
      .mockResolvedValueOnce(mockEmptyStreamResponse());
    vi.stubGlobal("fetch", fetchMock);

    render(<DataLoader />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: "Top 100" }));
    fireEvent.click(screen.getByRole("button", { name: "VN30" }));
    fireEvent.change(screen.getByRole("slider"), { target: { value: "4" } });
    fireEvent.click(await screen.findByRole("button", { name: /^load$/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(4));
    const calledUrls = fetchMock.mock.calls.map((call) => String(call[0] ?? ""));
    const hasVn30LoadCall = calledUrls.some(
      (url) => url.includes("/load-data") && url.includes("preset=VN30") && url.includes("years=4"),
    );
    expect(hasVn30LoadCall, `Unexpected fetch urls: ${calledUrls.join(" | ")}`).toBe(true);
  });

  it("shows explicit error on load HTTP failure", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(mockCachedEmptyResponse())
      .mockResolvedValueOnce({ ok: false, status: 500 } as Response);
    vi.stubGlobal("fetch", fetchMock);

    render(<DataLoader />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    fireEvent.click(await screen.findByRole("button", { name: /^load$/i }));
    await waitFor(() => expect(screen.getByText("Error: HTTP 500")).toBeInTheDocument());
  });

  it("marks cancelled when load request is aborted", async () => {
    const abortError = new Error("aborted");
    abortError.name = "AbortError";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(mockCachedEmptyResponse())
      .mockRejectedValueOnce(abortError);
    vi.stubGlobal("fetch", fetchMock);

    render(<DataLoader />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    fireEvent.click(await screen.findByRole("button", { name: /^load$/i }));
    await waitFor(() => expect(screen.getByText("Cancelled by user.")).toBeInTheDocument());
  });

  it("shows stop control while loading and aborts active stream", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(mockCachedEmptyResponse())
      .mockImplementationOnce((_url: string, options?: { signal?: AbortSignal }) => {
        return new Promise<Response>((_resolve, reject) => {
          options?.signal?.addEventListener("abort", () => {
            const error = new Error("aborted");
            error.name = "AbortError";
            reject(error);
          });
        });
      });
    vi.stubGlobal("fetch", fetchMock);

    render(<DataLoader />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    fireEvent.click(await screen.findByRole("button", { name: /^load$/i }));
    await waitFor(() => expect(screen.getByRole("button", { name: /^stop$/i })).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /^stop$/i }));

    await waitFor(() => expect(screen.getByText("Cancelled by user.")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /^load$/i })).toBeInTheDocument();
  });
});
