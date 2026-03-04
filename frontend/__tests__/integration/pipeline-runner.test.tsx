import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { PipelineRunner } from "@/app/screener/_components/pipeline-runner";
import { useUIStore } from "@/stores/ui-store";

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

describe("PipelineRunner integration", () => {
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
  });

  it("runs screener stream and renders completion summary", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      mockSseResponse([
        { event: "pipeline_start", data: { total_steps: 5, device: "CPU" } },
        { event: "agent_start", data: { step: 1, agent: "Screener Agent", icon: "search", detail: "running", device: "CPU", percent: 10 } },
        { event: "agent_done", data: { step: 1, percent: 20, duration_ms: 1200, result_count: 39 } },
        {
          event: "pipeline_complete",
          data: {
            total_symbols: 2,
            buy_count: 1,
            sell_count: 1,
            hold_count: 0,
            avg_score: 6.5,
            results: [
              { symbol: "AAA", score: 7.8, action: "BUY", rsi: 55, macd: "bullish", risk: "LOW", entry_price: 100, quantity: 100, order_type: "LO" },
              { symbol: "BBB", score: 5.2, action: "SELL", rsi: 73, macd: "bearish", risk: "HIGH", entry_price: 80, quantity: 100, order_type: "LO" },
            ],
          },
        },
      ]),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<PipelineRunner />);
    fireEvent.click(screen.getByRole("button", { name: /run pipeline/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(String(fetchMock.mock.calls[0]?.[0] ?? "")).toContain("/run-screener?preset=TOP100&mode=dry-run");

    await waitFor(() => expect(screen.getByText("Khuyến nghị MUA")).toBeInTheDocument());
    expect(screen.getByText("AAA")).toBeInTheDocument();
    expect(screen.getByText("BBB")).toBeInTheDocument();
  });

  it("renders explicit error panel when pipeline emits error event", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      mockSseResponse([
        { event: "pipeline_start", data: { total_steps: 5, device: "CPU" } },
        { event: "error", data: { message: "Screener failed: prompts missing" } },
      ]),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<PipelineRunner />);
    fireEvent.click(screen.getByRole("button", { name: /run pipeline/i }));

    await waitFor(() => expect(screen.getByText("Pipeline Error")).toBeInTheDocument());
    expect(screen.getByText(/prompts missing/i)).toBeInTheDocument();
  });
});

