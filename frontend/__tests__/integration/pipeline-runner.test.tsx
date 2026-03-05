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

function buildResults(count: number) {
  return Array.from({ length: count }).map((_, idx) => {
    const i = idx + 1;
    const action = i % 3 === 0 ? "HOLD" : i % 2 === 0 ? "SELL" : "BUY";
    return {
      symbol: `SYM${String(i).padStart(2, "0")}`,
      score: 10 - i * 0.2,
      action,
      rsi: 45 + (i % 25),
      macd: action === "BUY" ? "bullish" : action === "SELL" ? "bearish" : "neutral",
      risk: action === "BUY" ? "LOW" : action === "SELL" ? "HIGH" : "MEDIUM",
      entry_price: 20 + i,
      quantity: 100,
      order_type: "LO",
      reasoning: i === 1 ? "Sample AI rationale" : undefined,
    };
  });
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

  it("supports live mode query, filters, search reset, detail expand, and pagination", async () => {
    const results = buildResults(18);
    const fetchMock = vi.fn().mockResolvedValue(
      mockSseResponse([
        { event: "pipeline_start", data: { total_steps: 5, device: "CPU" } },
        { event: "agent_start", data: { step: 1, agent: "Screener Agent", icon: "search", detail: "running", device: "CPU", percent: 10 } },
        { event: "agent_progress", data: { step: 1, sub_percent: 40, percent: 40 } },
        { event: "agent_done", data: { step: 1, percent: 60, duration_ms: 1300, result_count: 18 } },
        {
          event: "pipeline_complete",
          data: {
            total_symbols: 18,
            buy_count: 6,
            sell_count: 6,
            hold_count: 6,
            avg_score: 6.8,
            results,
          },
        },
      ]),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<PipelineRunner />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "live" } });
    fireEvent.click(screen.getByRole("button", { name: /run pipeline/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(String(fetchMock.mock.calls[0]?.[0] ?? "")).toContain("mode=live");
    await waitFor(() => expect(screen.getByText("18 kết quả")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /^bán\s*\(\d+\)$/i }));
    await waitFor(() => expect(screen.getByText("6 kết quả")).toBeInTheDocument());

    fireEvent.change(screen.getByPlaceholderText("Tìm mã..."), { target: { value: "ZZZ" } });
    await waitFor(() => expect(screen.getByText("Không có mã nào khớp bộ lọc.")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /xóa bộ lọc/i }));
    await waitFor(() => expect(screen.getByText("18 kết quả")).toBeInTheDocument());

    fireEvent.click(screen.getByText("SYM01"));
    await waitFor(() => expect(screen.getByText("AI Analysis & Reasoning")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /cuối/i }));
    expect(screen.getByText(/Trang 2\/2/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /hiện chi tiết agents/i }));
    expect(screen.getByRole("button", { name: /ẩn chi tiết agents/i })).toBeInTheDocument();
  });

  it("supports stop action while running", async () => {
    const fetchMock = vi.fn().mockImplementation((_url: string, options?: { signal?: AbortSignal }) => {
      return new Promise<Response>((_resolve, reject) => {
        options?.signal?.addEventListener("abort", () => {
          const error = new Error("aborted");
          error.name = "AbortError";
          reject(error);
        });
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<PipelineRunner />);
    fireEvent.click(screen.getByRole("button", { name: /run pipeline/i }));
    await waitFor(() => expect(screen.getByRole("button", { name: /stop/i })).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /stop/i }));
    await waitFor(() => expect(screen.getByRole("button", { name: /run pipeline/i })).toBeInTheDocument());
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
