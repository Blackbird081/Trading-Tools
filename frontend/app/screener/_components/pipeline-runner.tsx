"use client";

import { useState, useCallback, useRef, useMemo } from "react";
import {
  Play,
  Search,
  BarChart3,
  Brain,
  Shield,
  Zap,
  CheckCircle2,
  Loader2,
  Cpu,
  CircuitBoard,
  Monitor,
  Clock,
  Square,
  ChevronDown,
  ChevronUp,
  ChevronLeft,
  ChevronRight,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Filter,
  TrendingUp,
  TrendingDown,
  Minus,
  Target,
  AlertTriangle,
  Activity,
} from "lucide-react";

import { useUIStore } from "@/stores/ui-store";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
const PAGE_SIZE = 15;

const AGENT_ICONS: Record<string, React.ReactNode> = {
  search: <Search className="h-4 w-4" />,
  chart: <BarChart3 className="h-4 w-4" />,
  brain: <Brain className="h-4 w-4" />,
  shield: <Shield className="h-4 w-4" />,
  zap: <Zap className="h-4 w-4" />,
};

const DEVICE_ICONS: Record<string, React.ReactNode> = {
  CPU: <Cpu className="h-3 w-3" />,
  NPU: <CircuitBoard className="h-3 w-3" />,
  GPU: <Monitor className="h-3 w-3" />,
};

const DEVICE_COLORS: Record<string, string> = {
  CPU: "text-blue-400 bg-blue-400/10",
  NPU: "text-fuchsia-400 bg-fuchsia-400/10",
  GPU: "text-amber-400 bg-amber-400/10",
};

interface AgentStep {
  step: number;
  agent: string;
  icon: string;
  detail: string;
  device: string;
  status: "pending" | "running" | "done";
  subPercent: number;
  durationMs: number;
  resultCount: number;
}

interface ScreenerResult {
  symbol: string;
  score: number;
  action: string;
  rsi: number;
  macd: string;
  risk: string;
  entry_price?: number;
  stop_loss?: number;
  take_profit?: number;
  sl_pct?: number;
  tp_pct?: number;
  quantity?: number;
  position_pct?: number;
  order_type?: string;
  vol_change_pct?: number;
  ma_trend?: string;
  reasoning?: string;
}

interface PipelineSummary {
  totalSymbols: number;
  buyCount: number;
  sellCount: number;
  holdCount: number;
  avgScore: number;
}

interface PipelineState {
  status: "idle" | "running" | "complete" | "error";
  percent: number;
  totalSteps: number;
  device: string;
  steps: AgentStep[];
  results: ScreenerResult[];
  summary: PipelineSummary | null;
  error: string;
}

type SortField = "symbol" | "score" | "action" | "rsi" | "risk" | "entry_price" | "quantity";
type SortDir = "asc" | "desc";
type ActionFilter = "ALL" | "BUY" | "SELL" | "HOLD";

/* ── Sortable Table Header ──────────────────────────────────── */
function SortHeader({
  label,
  field,
  currentField,
  currentDir,
  onSort,
  align = "left",
}: {
  label: string;
  field: SortField;
  currentField: SortField;
  currentDir: SortDir;
  onSort: (f: SortField) => void;
  align?: "left" | "right" | "center";
}) {
  const isActive = currentField === field;
  const alignCls =
    align === "right"
      ? "justify-end"
      : align === "center"
        ? "justify-center"
        : "justify-start";

  return (
    <th
      className="px-3 py-2.5 cursor-pointer select-none hover:bg-zinc-800/50 transition-colors"
      onClick={() => onSort(field)}
    >
      <div className={`flex items-center gap-1 ${alignCls}`}>
        <span
          className={`text-[11px] font-semibold uppercase tracking-wider ${isActive ? "text-emerald-400" : "text-zinc-500"}`}
        >
          {label}
        </span>
        {isActive ? (
          currentDir === "asc" ? (
            <ArrowUp className="h-3 w-3 text-emerald-400" />
          ) : (
            <ArrowDown className="h-3 w-3 text-emerald-400" />
          )
        ) : (
          <ArrowUpDown className="h-3 w-3 text-zinc-700" />
        )}
      </div>
    </th>
  );
}

/* ── Summary Card ──────────────────────────────────────────── */
function SummaryCard({
  label,
  value,
  icon,
  color,
  sub,
}: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  color: string;
  sub?: string;
}) {
  return (
    <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/60 p-4 flex items-start gap-3">
      <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${color}`}>
        {icon}
      </div>
      <div className="min-w-0">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">{label}</div>
        <div className="text-xl font-bold text-zinc-100 tabular-nums">{value}</div>
        {sub && <div className="text-[11px] text-zinc-500 mt-0.5">{sub}</div>}
      </div>
    </div>
  );
}

/* ── Expanded Detail Row ────────────────────────────────────── */
function DetailPanel({ r }: { r: ScreenerResult }) {
  return (
    <tr>
      <td colSpan={9} className="p-0">
        <div className="border-t border-zinc-800/30 bg-gradient-to-b from-zinc-900/80 to-zinc-900/40 px-5 py-4 space-y-4">
          {/* Metrics grid */}
          <div className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4 lg:grid-cols-8">
            <MetricCard label="Giá vào lệnh" value={r.entry_price?.toLocaleString("vi-VN")} unit="VND" />
            <MetricCard
              label={`Stop Loss (-${r.sl_pct ?? 7}%)`}
              value={r.stop_loss?.toLocaleString("vi-VN")}
              unit="VND"
              color="text-red-400"
            />
            <MetricCard
              label={`Take Profit (+${r.tp_pct ?? 10}%)`}
              value={r.take_profit?.toLocaleString("vi-VN")}
              unit="VND"
              color="text-emerald-400"
            />
            <MetricCard label="Khối lượng" value={r.quantity?.toLocaleString("vi-VN")} unit="cp" />
            <MetricCard label="Tỉ trọng" value={r.position_pct != null ? `${r.position_pct}%` : undefined} unit="NAV" />
            <MetricCard
              label="RSI (14)"
              value={r.rsi.toFixed(1)}
              color={r.rsi >= 70 ? "text-red-400" : r.rsi <= 30 ? "text-emerald-400" : "text-amber-300"}
            />
            <MetricCard
              label="Vol thay đổi"
              value={r.vol_change_pct != null ? `${r.vol_change_pct > 0 ? "+" : ""}${r.vol_change_pct}%` : undefined}
              color={r.vol_change_pct != null ? (r.vol_change_pct > 20 ? "text-emerald-400" : r.vol_change_pct < -10 ? "text-red-400" : "text-zinc-300") : undefined}
            />
            <MetricCard
              label="MA Trend"
              value={r.ma_trend?.replace(/_/g, " ")}
              color={r.ma_trend?.includes("above") || r.ma_trend?.includes("up") ? "text-emerald-400" : "text-red-400"}
            />
          </div>

          {/* AI Analysis */}
          {r.reasoning && (
            <div className="rounded-lg border border-zinc-800/60 bg-zinc-800/30 px-4 py-3">
              <div className="flex items-center gap-2 mb-2">
                <Brain className="h-3.5 w-3.5 text-fuchsia-400" />
                <span className="text-[10px] font-semibold uppercase tracking-wider text-fuchsia-400">
                  AI Analysis & Reasoning
                </span>
              </div>
              <p className="text-sm leading-relaxed text-zinc-300">{r.reasoning}</p>
            </div>
          )}

          {/* Order details */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-zinc-600">
            <span className="flex items-center gap-1">
              <span className="text-zinc-500">Loại lệnh:</span>
              <span className="text-zinc-400 font-medium">{r.order_type ?? "LO"}</span>
            </span>
            <span className="text-zinc-800">|</span>
            <span className="flex items-center gap-1">
              <span className="text-zinc-500">MACD:</span>
              <span className={`font-medium ${r.macd.includes("bullish") ? "text-emerald-400" : r.macd.includes("bearish") ? "text-red-400" : "text-zinc-400"}`}>
                {r.macd.replace(/_/g, " ")}
              </span>
            </span>
            <span className="text-zinc-800">|</span>
            <span className="flex items-center gap-1">
              <span className="text-zinc-500">Sàn:</span>
              <span className="text-zinc-400 font-medium">HOSE</span>
            </span>
            <span className="text-zinc-800">|</span>
            <span className="flex items-center gap-1">
              <span className="text-zinc-500">Mode:</span>
              <span className="text-amber-500 font-medium">dry-run</span>
            </span>
            <span className="text-zinc-800">|</span>
            <span className="flex items-center gap-1">
              <span className="text-zinc-500">Broker:</span>
              <span className="text-zinc-400 font-medium">SSI</span>
            </span>
          </div>
        </div>
      </td>
    </tr>
  );
}

function MetricCard({
  label,
  value,
  unit,
  color,
}: {
  label: string;
  value?: string;
  unit?: string;
  color?: string;
}) {
  return (
    <div>
      <div className="text-[10px] text-zinc-500 uppercase tracking-wide">{label}</div>
      <div className={`text-sm font-mono font-semibold ${color ?? "text-zinc-200"}`}>
        {value ?? "—"}
        {unit && value && (
          <span className="ml-1 text-[10px] text-zinc-600 font-normal">{unit}</span>
        )}
      </div>
    </div>
  );
}

/* ── Main Component ─────────────────────────────────────────── */
export function PipelineRunner() {
  const initialState: PipelineState = {
    status: "idle",
    percent: 0,
    totalSteps: 0,
    device: "CPU",
    steps: [],
    results: [],
    summary: null,
    error: "",
  };
  const [state, setState] = useState<PipelineState>(initialState);
  const abortRef = useRef<AbortController | null>(null);

  // Table state
  const [sortField, setSortField] = useState<SortField>("score");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [actionFilter, setActionFilter] = useState<ActionFilter>("ALL");
  const [expandedSymbol, setExpandedSymbol] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [showAgentSteps, setShowAgentSteps] = useState(true);

  const handleSort = useCallback(
    (field: SortField) => {
      if (sortField === field) {
        setSortDir((d) => (d === "asc" ? "desc" : "asc"));
      } else {
        setSortField(field);
        setSortDir(field === "symbol" ? "asc" : "desc");
      }
      setCurrentPage(1);
    },
    [sortField]
  );

  const sortedResults = useMemo(() => {
    let filtered = state.results;

    // Search filter
    if (searchQuery.trim()) {
      const q = searchQuery.trim().toUpperCase();
      filtered = filtered.filter((r) => r.symbol.includes(q));
    }

    // Action filter
    if (actionFilter !== "ALL") {
      filtered = filtered.filter((r) => r.action === actionFilter);
    }

    return [...filtered].sort((a, b) => {
      const dir = sortDir === "asc" ? 1 : -1;
      switch (sortField) {
        case "symbol":
          return dir * a.symbol.localeCompare(b.symbol);
        case "score":
          return dir * (a.score - b.score);
        case "action": {
          const order: Record<string, number> = { BUY: 0, HOLD: 1, SELL: 2 };
          return dir * ((order[a.action] ?? 1) - (order[b.action] ?? 1));
        }
        case "rsi":
          return dir * (a.rsi - b.rsi);
        case "risk": {
          const riskOrder: Record<string, number> = { LOW: 0, MEDIUM: 1, HIGH: 2 };
          return dir * ((riskOrder[a.risk] ?? 1) - (riskOrder[b.risk] ?? 1));
        }
        case "entry_price":
          return dir * ((a.entry_price ?? 0) - (b.entry_price ?? 0));
        case "quantity":
          return dir * ((a.quantity ?? 0) - (b.quantity ?? 0));
        default:
          return 0;
      }
    });
  }, [state.results, sortField, sortDir, actionFilter, searchQuery]);

  // Pagination
  const totalPages = Math.max(1, Math.ceil(sortedResults.length / PAGE_SIZE));
  const pagedResults = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE;
    return sortedResults.slice(start, start + PAGE_SIZE);
  }, [sortedResults, currentPage]);

  // Reset page when filter/search changes
  const handleFilterChange = useCallback((f: ActionFilter) => {
    setActionFilter(f);
    setCurrentPage(1);
  }, []);

  // ── SSE handling ──────────────────────────────────────────
  const preset = useUIStore((s) => s.preset);

  const handleRun = useCallback(async () => {
    if (state.status === "running") {
      abortRef.current?.abort();
      setState((s) => ({ ...s, status: "idle" }));
      return;
    }

    const controller = new AbortController();
    abortRef.current = controller;
    setExpandedSymbol(null);
    setSearchQuery("");
    setCurrentPage(1);
    setActionFilter("ALL");
    setShowAgentSteps(true);

    setState({
      ...initialState,
      status: "running",
    });

    try {
      const res = await fetch(`${API_BASE}/run-screener?preset=${preset}`, {
        signal: controller.signal,
      });
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        let eventType = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith("data: ") && eventType) {
            try {
              const data = JSON.parse(line.slice(6));
              handleEvent(eventType, data);
            } catch {
              // skip
            }
            eventType = "";
          }
        }
      }
    } catch (e) {
      if ((e as Error).name !== "AbortError") {
        setState((s) => ({
          ...s,
          status: "error",
          error: (e as Error).message,
        }));
      }
    }
  }, [state.status, preset]);

  const handleEvent = useCallback(
    (event: string, data: Record<string, unknown>) => {
      switch (event) {
        case "pipeline_start":
          setState((s) => ({
            ...s,
            totalSteps: data.total_steps as number,
            device: data.device as string,
          }));
          break;

        case "agent_start":
          setState((s) => {
            const newStep: AgentStep = {
              step: data.step as number,
              agent: data.agent as string,
              icon: data.icon as string,
              detail: data.detail as string,
              device: data.device as string,
              status: "running",
              subPercent: 0,
              durationMs: 0,
              resultCount: 0,
            };
            const steps = [...s.steps];
            const idx = steps.findIndex((st) => st.step === newStep.step);
            if (idx >= 0) steps[idx] = newStep;
            else steps.push(newStep);
            return { ...s, steps, percent: data.percent as number };
          });
          break;

        case "agent_progress":
          setState((s) => {
            const steps = s.steps.map((st) =>
              st.step === (data.step as number)
                ? { ...st, subPercent: data.sub_percent as number }
                : st
            );
            return { ...s, steps, percent: data.percent as number };
          });
          break;

        case "agent_done":
          setState((s) => {
            const steps = s.steps.map((st) =>
              st.step === (data.step as number)
                ? {
                  ...st,
                  status: "done" as const,
                  subPercent: 100,
                  durationMs: data.duration_ms as number,
                  resultCount: data.result_count as number,
                }
                : st
            );
            return { ...s, steps, percent: data.percent as number };
          });
          break;

        case "pipeline_complete":
          setState((s) => ({
            ...s,
            status: "complete",
            percent: 100,
            results: data.results as ScreenerResult[],
            summary: {
              totalSymbols: (data.total_symbols as number) ?? (data.results as ScreenerResult[]).length,
              buyCount: (data.buy_count as number) ?? 0,
              sellCount: (data.sell_count as number) ?? 0,
              holdCount: (data.hold_count as number) ?? 0,
              avgScore: (data.avg_score as number) ?? 0,
            },
          }));
          setShowAgentSteps(false);
          break;
      }
    },
    []
  );

  const isRunning = state.status === "running";
  const isDone = state.status === "complete";

  const buyCount = state.summary?.buyCount ?? state.results.filter((r) => r.action === "BUY").length;
  const sellCount = state.summary?.sellCount ?? state.results.filter((r) => r.action === "SELL").length;
  const holdCount = state.summary?.holdCount ?? state.results.filter((r) => r.action === "HOLD").length;

  return (
    <div className="space-y-4">
      {/* ── Control bar ──────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Screener Pipeline</h1>
          <p className="text-xs text-zinc-500">
            Multi-agent: Screener → Technical → AI → Risk → Executor
            {isDone && (
              <span className="ml-2 text-emerald-400 font-medium">
                · {preset} · {state.results.length} mã
              </span>
            )}
          </p>
        </div>
        <button
          onClick={handleRun}
          className={`flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-semibold transition-all shadow-lg ${isRunning
            ? "bg-red-600 hover:bg-red-500 text-white shadow-red-900/30"
            : "bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-900/30"
            }`}
        >
          {isRunning ? (
            <>
              <Square className="h-4 w-4" />
              Stop
            </>
          ) : (
            <>
              <Play className="h-4 w-4" />
              Run Pipeline
            </>
          )}
        </button>
      </div>

      {/* ── Global progress bar ──────────────────────────────── */}
      {(isRunning || isDone) && (
        <div className="space-y-1">
          <div className="relative h-2 overflow-hidden rounded-full bg-zinc-800">
            <div
              className={`absolute inset-y-0 left-0 rounded-full transition-all duration-200 ${isDone
                ? "bg-emerald-500"
                : "bg-gradient-to-r from-emerald-600 via-emerald-400 to-emerald-600"
                }`}
              style={{ width: `${state.percent}%` }}
            />
            {isRunning && (
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent animate-[shimmer_1.5s_infinite]" />
            )}
          </div>
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-zinc-500">
              {isDone ? "Pipeline complete" : `Running... ${Math.round(state.percent)}%`}
            </span>
            <span
              className={`inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[10px] font-medium ${DEVICE_COLORS[state.device] ?? "text-zinc-400 bg-zinc-800"}`}
            >
              {DEVICE_ICONS[state.device]}
              {state.device}
            </span>
          </div>
        </div>
      )}

      {/* ── Agent steps (collapsible) ────────────────────────── */}
      {state.steps.length > 0 && (
        <div>
          {isDone && (
            <button
              onClick={() => setShowAgentSteps((v) => !v)}
              className="mb-2 flex items-center gap-1 text-[11px] text-zinc-500 hover:text-zinc-300 transition-colors"
            >
              {showAgentSteps ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              {showAgentSteps ? "Ẩn chi tiết agents" : "Hiện chi tiết agents"}
            </button>
          )}
          {(showAgentSteps || isRunning) && (
            <div className="space-y-1.5">
              {state.steps.map((step) => (
                <div
                  key={step.step}
                  className={`rounded-lg border p-2.5 transition-colors ${step.status === "running"
                    ? "border-emerald-700/60 bg-emerald-950/30"
                    : "border-zinc-800/60 bg-zinc-900/40"
                    }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div
                        className={`flex h-6 w-6 items-center justify-center rounded ${step.status === "running"
                          ? "bg-emerald-600/20 text-emerald-400"
                          : "bg-zinc-800 text-emerald-500"
                          }`}
                      >
                        {step.status === "running" ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <CheckCircle2 className="h-3.5 w-3.5" />
                        )}
                      </div>
                      <span className="text-xs font-medium text-zinc-300">{step.agent}</span>
                      <span
                        className={`inline-flex items-center gap-0.5 rounded px-1 py-0.5 text-[9px] font-medium ${DEVICE_COLORS[step.device] ?? "text-zinc-400 bg-zinc-800"}`}
                      >
                        {DEVICE_ICONS[step.device]}
                        {step.device}
                      </span>
                    </div>
                    <div className="text-right text-[11px]">
                      {step.status === "done" && (
                        <span className="text-zinc-500">
                          {(step.durationMs / 1000).toFixed(1)}s · {step.resultCount} results
                        </span>
                      )}
                      {step.status === "running" && (
                        <span className="font-mono text-emerald-400">{Math.round(step.subPercent)}%</span>
                      )}
                    </div>
                  </div>
                  {step.status === "running" && (
                    <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-zinc-800">
                      <div
                        className="h-full rounded-full bg-emerald-500/80 transition-all duration-200"
                        style={{ width: `${step.subPercent}%` }}
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Summary Cards ────────────────────────────────────── */}
      {isDone && state.summary && (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
          <SummaryCard
            label="Tổng mã phân tích"
            value={state.summary.totalSymbols}
            icon={<Target className="h-5 w-5 text-blue-400" />}
            color="bg-blue-500/10"
            sub={`Preset: ${preset}`}
          />
          <SummaryCard
            label="Khuyến nghị MUA"
            value={buyCount}
            icon={<TrendingUp className="h-5 w-5 text-emerald-400" />}
            color="bg-emerald-500/10"
            sub={`${state.summary.totalSymbols > 0 ? Math.round(buyCount / state.summary.totalSymbols * 100) : 0}% tổng mã`}
          />
          <SummaryCard
            label="Khuyến nghị BÁN"
            value={sellCount}
            icon={<TrendingDown className="h-5 w-5 text-red-400" />}
            color="bg-red-500/10"
            sub={`${state.summary.totalSymbols > 0 ? Math.round(sellCount / state.summary.totalSymbols * 100) : 0}% tổng mã`}
          />
          <SummaryCard
            label="Giữ / Theo dõi"
            value={holdCount}
            icon={<Minus className="h-5 w-5 text-amber-400" />}
            color="bg-amber-500/10"
            sub={`${state.summary.totalSymbols > 0 ? Math.round(holdCount / state.summary.totalSymbols * 100) : 0}% tổng mã`}
          />
          <SummaryCard
            label="Điểm trung bình"
            value={`${state.summary.avgScore}/10`}
            icon={<Activity className="h-5 w-5 text-fuchsia-400" />}
            color="bg-fuchsia-500/10"
            sub={state.summary.avgScore >= 6 ? "Tích cực" : state.summary.avgScore >= 4.5 ? "Trung tính" : "Tiêu cực"}
          />
        </div>
      )}

      {/* ── Results Table ────────────────────────────────────── */}
      {isDone && state.results.length > 0 && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/80 overflow-hidden">
          {/* Toolbar: search + filters */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-800 px-4 py-3">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-500" />
              <input
                type="text"
                placeholder="Tìm mã..."
                value={searchQuery}
                onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1); }}
                className="h-8 w-48 rounded-lg border border-zinc-700 bg-zinc-800/80 pl-8 pr-3 text-xs text-zinc-200 placeholder-zinc-600 outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600/30 transition-colors"
              />
            </div>

            {/* Filter + count */}
            <div className="flex items-center gap-2">
              <span className="text-[11px] text-zinc-500 mr-1">
                {sortedResults.length} kết quả
              </span>
              <div className="flex items-center gap-1 rounded-lg border border-zinc-800 bg-zinc-900/60 p-0.5">
                {(["ALL", "BUY", "SELL", "HOLD"] as ActionFilter[]).map((f) => {
                  const count =
                    f === "ALL"
                      ? state.results.length
                      : f === "BUY"
                        ? buyCount
                        : f === "SELL"
                          ? sellCount
                          : holdCount;
                  const isActive = actionFilter === f;
                  const colorCls =
                    f === "BUY"
                      ? isActive ? "bg-emerald-600 text-white shadow-sm" : "text-emerald-400 hover:bg-zinc-800"
                      : f === "SELL"
                        ? isActive ? "bg-red-600 text-white shadow-sm" : "text-red-400 hover:bg-zinc-800"
                        : f === "HOLD"
                          ? isActive ? "bg-amber-600 text-white shadow-sm" : "text-amber-400 hover:bg-zinc-800"
                          : isActive ? "bg-zinc-700 text-white shadow-sm" : "text-zinc-400 hover:bg-zinc-800";
                  return (
                    <button
                      key={f}
                      onClick={() => handleFilterChange(f)}
                      className={`rounded-md px-2.5 py-1 text-[10px] font-semibold transition-all ${colorCls}`}
                    >
                      {f === "ALL" ? "Tất cả" : f === "BUY" ? "MUA" : f === "SELL" ? "BÁN" : "GIỮ"}
                      <span className="ml-1 opacity-60">({count})</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-zinc-800 bg-zinc-900/50">
                  <th className="w-8 px-2 py-2.5" />
                  <SortHeader label="Mã" field="symbol" currentField={sortField} currentDir={sortDir} onSort={handleSort} />
                  <SortHeader label="Đề xuất" field="action" currentField={sortField} currentDir={sortDir} onSort={handleSort} align="center" />
                  <SortHeader label="Score" field="score" currentField={sortField} currentDir={sortDir} onSort={handleSort} align="right" />
                  <SortHeader label="Giá vào" field="entry_price" currentField={sortField} currentDir={sortDir} onSort={handleSort} align="right" />
                  <SortHeader label="RSI" field="rsi" currentField={sortField} currentDir={sortDir} onSort={handleSort} align="right" />
                  <SortHeader label="Risk" field="risk" currentField={sortField} currentDir={sortDir} onSort={handleSort} align="center" />
                  <SortHeader label="KL" field="quantity" currentField={sortField} currentDir={sortDir} onSort={handleSort} align="right" />
                  <th className="px-3 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-zinc-500 text-right">Lệnh</th>
                </tr>
              </thead>
              {pagedResults.map((r, idx) => {
                const isExpanded = expandedSymbol === r.symbol;
                const rowNum = (currentPage - 1) * PAGE_SIZE + idx + 1;
                return (
                  <tbody key={r.symbol}>
                    <tr
                      onClick={() => setExpandedSymbol(isExpanded ? null : r.symbol)}
                      className={`cursor-pointer transition-colors ${isExpanded ? "bg-zinc-800/50" : "hover:bg-zinc-800/30"
                        } ${r.action === "BUY"
                          ? "border-l-2 border-l-emerald-500"
                          : r.action === "SELL"
                            ? "border-l-2 border-l-red-500"
                            : "border-l-2 border-l-zinc-700"
                        }`}
                    >
                      {/* Row number */}
                      <td className="px-2 py-2.5 text-center">
                        <span className="text-[10px] text-zinc-600 tabular-nums">{rowNum}</span>
                      </td>

                      {/* Symbol */}
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-2">
                          {isExpanded ? (
                            <ChevronUp className="h-3 w-3 text-zinc-500" />
                          ) : (
                            <ChevronDown className="h-3 w-3 text-zinc-600" />
                          )}
                          <span className="text-sm font-bold text-amber-300">{r.symbol}</span>
                        </div>
                      </td>

                      {/* Action */}
                      <td className="px-3 py-2.5 text-center">
                        <span
                          className={`inline-flex items-center gap-1 rounded-md px-2.5 py-0.5 text-[11px] font-bold ${r.action === "BUY"
                            ? "bg-emerald-600/90 text-white"
                            : r.action === "SELL"
                              ? "bg-red-600/90 text-white"
                              : "bg-zinc-700 text-zinc-300"
                            }`}
                        >
                          {r.action === "BUY" ? (
                            <><TrendingUp className="h-3 w-3" /> MUA</>
                          ) : r.action === "SELL" ? (
                            <><TrendingDown className="h-3 w-3" /> BÁN</>
                          ) : (
                            <><Minus className="h-3 w-3" /> GIỮ</>
                          )}
                        </span>
                      </td>

                      {/* Score with mini bar */}
                      <td className="px-3 py-2.5 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="hidden sm:block w-12 h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                            <div
                              className={`h-full rounded-full ${r.score >= 7 ? "bg-emerald-500" : r.score >= 4.5 ? "bg-amber-500" : "bg-red-500"
                                }`}
                              style={{ width: `${r.score * 10}%` }}
                            />
                          </div>
                          <span
                            className={`text-sm font-bold font-mono ${r.score >= 7 ? "text-emerald-400" : r.score >= 4.5 ? "text-amber-400" : "text-red-400"
                              }`}
                          >
                            {r.score.toFixed(1)}
                          </span>
                        </div>
                      </td>

                      {/* Entry price */}
                      <td className="px-3 py-2.5 text-right font-mono text-sm text-zinc-300">
                        {r.entry_price?.toLocaleString("vi-VN") ?? "—"}
                      </td>

                      {/* RSI */}
                      <td className="px-3 py-2.5 text-right">
                        <span
                          className={`text-sm font-mono ${r.rsi >= 70 ? "text-red-400" : r.rsi <= 30 ? "text-emerald-400" : "text-zinc-300"
                            }`}
                        >
                          {r.rsi.toFixed(1)}
                        </span>
                      </td>

                      {/* Risk */}
                      <td className="px-3 py-2.5 text-center">
                        <span
                          className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${r.risk === "LOW"
                            ? "bg-emerald-900/40 text-emerald-400"
                            : r.risk === "MEDIUM"
                              ? "bg-amber-900/40 text-amber-400"
                              : "bg-red-900/40 text-red-400"
                            }`}
                        >
                          {r.risk === "HIGH" && <AlertTriangle className="h-2.5 w-2.5" />}
                          {r.risk}
                        </span>
                      </td>

                      {/* Quantity */}
                      <td className="px-3 py-2.5 text-right font-mono text-sm text-zinc-300">
                        {r.quantity?.toLocaleString("vi-VN") ?? "—"}
                      </td>

                      {/* Order type */}
                      <td className="px-3 py-2.5 text-right">
                        <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] font-mono text-zinc-400">
                          {r.order_type ?? "LO"}
                        </span>
                      </td>
                    </tr>

                    {/* Expanded detail row */}
                    {isExpanded && <DetailPanel r={r} />}
                  </tbody>
                );
              })}
            </table>
          </div>

          {/* Empty filter state */}
          {sortedResults.length === 0 && (
            <div className="flex items-center justify-center py-8 text-sm text-zinc-500">
              Không có mã nào khớp bộ lọc.
              <button
                onClick={() => { setActionFilter("ALL"); setSearchQuery(""); }}
                className="ml-2 text-emerald-400 hover:underline"
              >
                Xóa bộ lọc
              </button>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-zinc-800 px-4 py-2.5">
              <span className="text-[11px] text-zinc-500">
                Trang {currentPage}/{totalPages} · Hiển thị {(currentPage - 1) * PAGE_SIZE + 1}–{Math.min(currentPage * PAGE_SIZE, sortedResults.length)} / {sortedResults.length}
              </span>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setCurrentPage(1)}
                  disabled={currentPage === 1}
                  className="rounded px-2 py-1 text-[11px] text-zinc-400 hover:bg-zinc-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  Đầu
                </button>
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="rounded p-1 text-zinc-400 hover:bg-zinc-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                {/* Page numbers */}
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  let page: number;
                  if (totalPages <= 5) {
                    page = i + 1;
                  } else if (currentPage <= 3) {
                    page = i + 1;
                  } else if (currentPage >= totalPages - 2) {
                    page = totalPages - 4 + i;
                  } else {
                    page = currentPage - 2 + i;
                  }
                  return (
                    <button
                      key={page}
                      onClick={() => setCurrentPage(page)}
                      className={`min-w-[28px] rounded px-1.5 py-1 text-[11px] font-medium transition-colors ${page === currentPage
                        ? "bg-emerald-600 text-white"
                        : "text-zinc-400 hover:bg-zinc-800"
                        }`}
                    >
                      {page}
                    </button>
                  );
                })}
                <button
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="rounded p-1 text-zinc-400 hover:bg-zinc-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
                <button
                  onClick={() => setCurrentPage(totalPages)}
                  disabled={currentPage === totalPages}
                  className="rounded px-2 py-1 text-[11px] text-zinc-400 hover:bg-zinc-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  Cuối
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Idle state ───────────────────────────────────────── */}
      {state.status === "idle" && state.steps.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-zinc-800 py-20 text-center">
          <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-600/20 to-emerald-600/5 ring-1 ring-emerald-600/20">
            <Play className="h-7 w-7 text-emerald-500" />
          </div>
          <p className="text-sm text-zinc-400">
            Nhấn <strong className="text-zinc-200">Run Pipeline</strong> để phân tích toàn bộ danh sách <strong className="text-emerald-400">{preset}</strong>
          </p>
          <p className="mt-2 text-xs text-zinc-600 max-w-md">
            5 agents sẽ phân tích tất cả mã đã load: Screener → Technical → AI (LLM trên {state.device}) → Risk → Executor
          </p>
        </div>
      )}

      {/* ── Error state ──────────────────────────────────────── */}
      {state.status === "error" && (
        <div className="rounded-xl border border-red-900/50 bg-red-950/30 p-4 flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-red-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-red-400">Pipeline Error</p>
            <p className="text-xs text-red-400/70 mt-1">{state.error}</p>
          </div>
        </div>
      )}
    </div>
  );
}
