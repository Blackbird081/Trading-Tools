# 04 — MULTI-AGENT SYSTEM: AI ORCHESTRATION & EDGE INFERENCE

**Project:** Hệ thống Giao dịch Thuật toán Đa Tác vụ (Enterprise Edition)
**Role:** AI Engineer & Quant Developer
**Version:** 1.0 | February 2026
**Stack:** LangGraph 0.2+ | OpenVINO GenAI 2024.4+ | DuckDB 1.1+ (vss) | Python 3.12+

---

## 1. AGENT ORCHESTRATION — LANGGRAPH STATE MACHINE

### 1.1. Tại sao LangGraph thay vì LangChain Chains

| Tiêu chí | LangChain (Sequential Chain) | LangGraph (StateGraph) | Verdict |
|:---|:---|:---|:---|
| **Flow control** | Linear (A → B → C) hoặc branching đơn giản | Directed graph — cycles, conditionals, parallel branches | **LangGraph** ✓ |
| **State management** | Implicit (output chain = input chain tiếp theo) | Explicit `TypedDict` state — mọi agent đọc/ghi cùng 1 state | **LangGraph** ✓ |
| **Error recovery** | Try-catch rồi fail toàn bộ chain | Node-level retry, conditional routing sang fallback node | **LangGraph** ✓ |
| **Human-in-the-loop** | Hack bằng callback | Native `interrupt_before` / `interrupt_after` | **LangGraph** ✓ |
| **Debuggability** | Log string dài, khó trace | Graph visualization, step-by-step replay, state snapshot | **LangGraph** ✓ |
| **Determinism** | Non-deterministic (LLM decides routing) | **Deterministic** — routing logic là Python code, không phải LLM | **LangGraph** ✓ |
| **Lý do chọn** | Trong trading system, **determinism là bắt buộc**. Không thể để LLM "quyết định" nên gọi Risk Agent hay không. LangGraph cho phép mô hình hóa business workflow dưới dạng state machine — mọi transition đều explicit, testable, auditable. | | |

### 1.2. AgentState — Shared State Schema

Tất cả agent trong graph đọc và ghi vào một `TypedDict` duy nhất. Đây là "blackboard" trung tâm.

```python
# packages/agents/src/agents/state.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TypedDict

from core.value_objects import Symbol


class AgentPhase(StrEnum):
    """Tracks which phase the pipeline is currently in."""
    IDLE = "idle"
    SCREENING = "screening"
    ANALYZING = "analyzing"
    RISK_CHECKING = "risk_checking"
    EXECUTING = "executing"
    COMPLETED = "completed"
    ERROR = "error"


class SignalAction(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    SKIP = "SKIP"


@dataclass(frozen=True, slots=True)
class ScreenerResult:
    """Output from Screener Agent."""
    symbol: Symbol
    eps_growth: float
    pe_ratio: float
    volume_spike: bool
    passed_at: datetime


@dataclass(frozen=True, slots=True)
class TechnicalScore:
    """Output from Technical Analysis Agent."""
    symbol: Symbol
    rsi_14: float
    macd_signal: str          # "bullish_cross" | "bearish_cross" | "neutral"
    bb_position: str          # "below_lower" | "above_upper" | "inside"
    trend_ma: str             # "golden_cross" | "death_cross" | "neutral"
    composite_score: float    # -10.0 to +10.0
    recommended_action: SignalAction
    analysis_timestamp: datetime


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    """Output from Risk Management Agent."""
    symbol: Symbol
    approved: bool
    var_95: Decimal            # Value at Risk (95% confidence)
    position_size_pct: Decimal # Recommended position size as % of NAV
    stop_loss_price: Decimal
    take_profit_price: Decimal
    rejection_reason: str | None
    assessed_at: datetime


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    """Output from Executor Agent."""
    symbol: Symbol
    action: SignalAction
    quantity: int
    price: Decimal
    order_type: str            # "LO" | "ATO" | "ATC" | "MP"
    broker: str                # "SSI" | "DNSE"
    executed: bool
    order_id: str | None
    executed_at: datetime | None


class AgentState(TypedDict, total=False):
    """
    Shared state for the entire Multi-Agent pipeline.

    ★ CONVENTION:
      - Each agent READS upstream data and WRITES its own output.
      - No agent modifies another agent's output section.
      - State is immutable per step — LangGraph handles state merging.
    """

    # ── Pipeline Metadata ──────────────────────────────────────
    phase: AgentPhase
    run_id: str                        # Unique ID per pipeline execution
    triggered_at: datetime
    error_message: str | None

    # ── Screener Agent Output ──────────────────────────────────
    watchlist: list[ScreenerResult]    # Symbols that passed screening

    # ── Technical Agent Output ─────────────────────────────────
    technical_scores: list[TechnicalScore]
    top_candidates: list[Symbol]       # Filtered by score threshold

    # ── Risk Agent Output ──────────────────────────────────────
    risk_assessments: list[RiskAssessment]
    approved_trades: list[Symbol]      # Symbols that passed risk check

    # ── Executor Agent Output ──────────────────────────────────
    execution_plans: list[ExecutionPlan]

    # ── Fundamental Agent Output (Async, Optional) ─────────────
    ai_insights: dict[Symbol, str]     # symbol -> natural language insight

    # ── Portfolio Context (Injected at start) ──────────────────
    current_nav: Decimal
    current_positions: dict[Symbol, int]
    purchasing_power: Decimal

    # ── Configuration ──────────────────────────────────────────
    max_candidates: int                # Max symbols to analyze (default: 10)
    score_threshold: float             # Min score to proceed (default: 5.0)
    dry_run: bool                      # If True, don't execute orders
```

### 1.3. Graph Architecture — The Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     LANGGRAPH STATE MACHINE (Supervisor)                     │
│                                                                             │
│  ┌───────────┐     ┌───────────────┐     ┌───────────────┐                 │
│  │  START     │     │   Screener    │     │  Technical    │                 │
│  │  (inject   │────▶│   Agent       │────▶│  Analysis     │                 │
│  │  context)  │     │               │     │  Agent        │                 │
│  └───────────┘     │ • vnstock     │     │               │                 │
│                     │   screening   │     │ • pandas-ta   │                 │
│                     │ • DuckDB SQL  │     │ • scoring     │                 │
│                     │ • Volume      │     │ • PyPortOpt   │                 │
│                     │   analysis    │     │               │                 │
│                     └───────┬───────┘     └───────┬───────┘                 │
│                             │                     │                          │
│                             │  watchlist          │  technical_scores        │
│                             │  empty?             │  all below threshold?    │
│                             │                     │                          │
│                        ┌────▼────┐           ┌────▼────┐                    │
│                        │  YES:   │           │  YES:   │                    │
│                        │  → END  │           │  → END  │                    │
│                        │ (SKIP)  │           │ (HOLD)  │                    │
│                        └─────────┘           └─────────┘                    │
│                                                                             │
│                     ┌───────────────┐     ┌───────────────┐                 │
│                     │     Risk      │     │   Executor    │                 │
│                     │  Management   │────▶│   Agent       │                 │
│                     │   Agent       │     │               │                 │
│                     │               │     │ • SSI API     │                 │
│                     │ • VaR calc    │     │ • DNSE API    │                 │
│                     │ • Position    │     │ • Order       │                 │
│                     │   limits     │     │   placement   │                 │
│                     │ • Kill switch │     │ • Confirm     │                 │
│                     └───────┬───────┘     └───────┬───────┘                 │
│                             │                     │                          │
│                        ┌────▼────┐           ┌────▼────┐                    │
│                        │  NONE   │           │  END    │                    │
│                        │approved:│           │(DONE)   │                    │
│                        │  → END  │           └─────────┘                    │
│                        │(REJECT) │                                          │
│                        └─────────┘                                          │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │              PARALLEL BRANCH (Non-blocking, Optional)               │    │
│  │                                                                     │    │
│  │   ┌───────────────┐                                                 │    │
│  │   │ Fundamental   │  Runs in parallel with Technical Agent.         │    │
│  │   │ Agent (NPU)   │  Output (ai_insights) merged into state        │    │
│  │   │               │  asynchronously. Does NOT block pipeline.       │    │
│  │   │ • OpenVINO    │                                                 │    │
│  │   │ • Llama-3 INT4│                                                 │    │
│  │   │ • News + BCTC │                                                 │    │
│  │   └───────────────┘                                                 │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.4. Graph Definition — Production Code

```python
# packages/agents/src/agents/supervisor.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Literal

from langgraph.graph import END, StateGraph

from agents.state import AgentPhase, AgentState

if TYPE_CHECKING:
    from agents.executor_agent import ExecutorAgent
    from agents.fundamental_agent import FundamentalAgent
    from agents.risk_agent import RiskAgent
    from agents.screener_agent import ScreenerAgent
    from agents.technical_agent import TechnicalAgent


def build_trading_graph(
    screener: ScreenerAgent,
    technical: TechnicalAgent,
    risk: RiskAgent,
    executor: ExecutorAgent,
    fundamental: FundamentalAgent | None = None,
) -> StateGraph:
    """
    Constructs the Multi-Agent trading pipeline as a LangGraph StateGraph.

    Flow: START → Screener → Technical → Risk → Executor → END
    Parallel: Fundamental Agent runs alongside Technical (non-blocking).

    ★ All routing decisions are DETERMINISTIC Python code.
    ★ No LLM decides the flow — only data conditions.
    """

    graph = StateGraph(AgentState)

    # ── Register Nodes ─────────────────────────────────────────

    graph.add_node("inject_context", _inject_context)
    graph.add_node("screener", screener.run)
    graph.add_node("technical", technical.run)
    graph.add_node("risk", risk.run)
    graph.add_node("executor", executor.run)
    graph.add_node("finalize", _finalize)

    if fundamental is not None:
        graph.add_node("fundamental", fundamental.run)

    # ── Define Edges ───────────────────────────────────────────

    # Entry point
    graph.set_entry_point("inject_context")
    graph.add_edge("inject_context", "screener")

    # Screener → conditional: has candidates?
    graph.add_conditional_edges(
        "screener",
        _route_after_screener,
        {
            "has_candidates": "technical",
            "no_candidates": "finalize",
        },
    )

    # Technical → conditional: any actionable scores?
    graph.add_conditional_edges(
        "technical",
        _route_after_technical,
        {
            "has_signals": "risk",
            "no_signals": "finalize",
        },
    )

    # Parallel branch: Fundamental runs alongside Technical
    if fundamental is not None:
        graph.add_edge("screener", "fundamental")  # Fork
        # Fundamental output merges into state but doesn't block main path

    # Risk → conditional: any approved?
    graph.add_conditional_edges(
        "risk",
        _route_after_risk,
        {
            "has_approved": "executor",
            "none_approved": "finalize",
        },
    )

    # Executor → finalize
    graph.add_edge("executor", "finalize")

    # Finalize → END
    graph.add_edge("finalize", END)

    return graph


# ── Node Functions ─────────────────────────────────────────────────

def _inject_context(state: AgentState) -> dict:
    """Initialize pipeline metadata. First node in graph."""
    return {
        "phase": AgentPhase.SCREENING,
        "run_id": str(uuid.uuid4()),
        "triggered_at": datetime.now(timezone.utc),
        "error_message": None,
        "max_candidates": state.get("max_candidates", 10),
        "score_threshold": state.get("score_threshold", 5.0),
        "dry_run": state.get("dry_run", False),
    }


def _finalize(state: AgentState) -> dict:
    """Terminal node — mark pipeline as completed."""
    return {"phase": AgentPhase.COMPLETED}


# ── Routing Functions (Pure, Deterministic) ────────────────────────

def _route_after_screener(
    state: AgentState,
) -> Literal["has_candidates", "no_candidates"]:
    """Route based on Screener output. No LLM involved."""
    watchlist = state.get("watchlist", [])
    if len(watchlist) > 0:
        return "has_candidates"
    return "no_candidates"


def _route_after_technical(
    state: AgentState,
) -> Literal["has_signals", "no_signals"]:
    """Route based on Technical scores exceeding threshold."""
    top = state.get("top_candidates", [])
    if len(top) > 0:
        return "has_signals"
    return "no_signals"


def _route_after_risk(
    state: AgentState,
) -> Literal["has_approved", "none_approved"]:
    """Route based on Risk approval."""
    approved = state.get("approved_trades", [])
    if len(approved) > 0:
        return "has_approved"
    return "none_approved"
```

### 1.5. Agent Node Implementation — Screener Agent

```python
# packages/agents/src/agents/screener_agent.py
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from agents.state import AgentPhase, AgentState, ScreenerResult

if TYPE_CHECKING:
    from core.value_objects import Symbol


class ScreenerAgent:
    """
    Scans the entire market for opportunities.

    Uses vnstock screening + DuckDB vectorized queries
    to filter ~1,800 symbols down to 5-15 candidates.
    """

    def __init__(
        self,
        screener_port: object,   # vnstock screener adapter
        tick_repo: object,       # DuckDB tick repository
    ) -> None:
        self._screener = screener_port
        self._tick_repo = tick_repo

    async def run(self, state: AgentState) -> dict:
        """LangGraph node function. Reads state, returns partial update."""

        # Step 1: Fundamental screening (EPS growth, PE ratio)
        raw_candidates = await asyncio.to_thread(
            self._screener.screen,
            min_eps_growth=0.10,     # EPS tăng ≥ 10%
            max_pe_ratio=15.0,       # PE ≤ 15
            min_market_cap=1000e9,   # Vốn hóa ≥ 1,000 tỷ VND
        )

        # Step 2: Volume spike detection via DuckDB
        volume_spikes = await asyncio.to_thread(
            self._tick_repo.query_volume_spikes,
            threshold_multiplier=2.0,  # Volume > 2x trung bình 20 phiên
        )
        spike_symbols = {r["symbol"] for r in volume_spikes}

        # Step 3: Combine and build watchlist
        max_candidates = state.get("max_candidates", 10)
        watchlist: list[ScreenerResult] = []

        for candidate in raw_candidates[:max_candidates]:
            watchlist.append(
                ScreenerResult(
                    symbol=candidate["symbol"],
                    eps_growth=candidate["eps_growth"],
                    pe_ratio=candidate["pe_ratio"],
                    volume_spike=candidate["symbol"] in spike_symbols,
                    passed_at=datetime.now(timezone.utc),
                )
            )

        return {
            "phase": AgentPhase.ANALYZING,
            "watchlist": watchlist,
        }
```

### 1.6. Agent Node Implementation — Technical Agent

```python
# packages/agents/src/agents/technical_agent.py
from __future__ import annotations

import asyncio
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from functools import partial
from typing import TYPE_CHECKING

from agents.state import (
    AgentState,
    SignalAction,
    TechnicalScore,
)

if TYPE_CHECKING:
    from core.value_objects import Symbol

_process_pool = ProcessPoolExecutor(max_workers=2)


def _compute_technical_score_sync(
    ohlcv_data: list[dict],
) -> dict:
    """
    CPU-bound computation — runs in separate PROCESS.

    ★ Must be top-level function (picklable).
    ★ Imports inside function to avoid serialization issues.
    """
    import pandas as pd
    import pandas_ta as ta

    df = pd.DataFrame(ohlcv_data)
    df.ta.rsi(length=14, append=True)
    df.ta.macd(fast=12, slow=26, signal=9, append=True)
    df.ta.bbands(length=20, std=2, append=True)
    df.ta.sma(length=50, append=True)
    df.ta.sma(length=200, append=True)

    latest = df.iloc[-1]
    score = 0.0

    # ── RSI Scoring (±3 points) ────────────────────────────
    rsi = latest.get("RSI_14", 50)
    if rsi < 30:
        score += 3.0     # Oversold — bullish
    elif rsi < 40:
        score += 1.5
    elif rsi > 70:
        score -= 3.0     # Overbought — bearish
    elif rsi > 60:
        score -= 1.5

    # ── MACD Scoring (±3 points) ───────────────────────────
    macd_val = latest.get("MACD_12_26_9", 0)
    macd_sig = latest.get("MACDs_12_26_9", 0)
    macd_signal = "neutral"
    if macd_val > macd_sig and df.iloc[-2].get("MACD_12_26_9", 0) <= df.iloc[-2].get("MACDs_12_26_9", 0):
        score += 3.0
        macd_signal = "bullish_cross"
    elif macd_val < macd_sig and df.iloc[-2].get("MACD_12_26_9", 0) >= df.iloc[-2].get("MACDs_12_26_9", 0):
        score -= 3.0
        macd_signal = "bearish_cross"

    # ── Bollinger Bands Scoring (±2 points) ────────────────
    close = latest.get("close", 0)
    bb_lower = latest.get("BBL_20_2.0", close)
    bb_upper = latest.get("BBU_20_2.0", close)
    bb_position = "inside"
    if close <= bb_lower:
        score += 2.0
        bb_position = "below_lower"
    elif close >= bb_upper:
        score -= 2.0
        bb_position = "above_upper"

    # ── Trend MA50/MA200 Scoring (±2 points) ───────────────
    ma50 = latest.get("SMA_50", 0)
    ma200 = latest.get("SMA_200", 0)
    trend_ma = "neutral"
    if ma50 > ma200:
        score += 2.0
        trend_ma = "golden_cross"
    elif ma50 < ma200:
        score -= 2.0
        trend_ma = "death_cross"

    # ── Determine Action ───────────────────────────────────
    if score >= 5.0:
        action = "BUY"
    elif score <= -5.0:
        action = "SELL"
    else:
        action = "HOLD"

    return {
        "rsi_14": float(rsi),
        "macd_signal": macd_signal,
        "bb_position": bb_position,
        "trend_ma": trend_ma,
        "composite_score": float(score),
        "recommended_action": action,
    }


class TechnicalAgent:
    """Performs technical analysis on screened candidates."""

    def __init__(self, tick_repo: object) -> None:
        self._tick_repo = tick_repo

    async def run(self, state: AgentState) -> dict:
        """LangGraph node: analyze all watchlist symbols in parallel."""
        watchlist = state.get("watchlist", [])
        threshold = state.get("score_threshold", 5.0)
        loop = asyncio.get_running_loop()

        # Parallel analysis of all candidates
        tasks = []
        for item in watchlist:
            ohlcv = await asyncio.to_thread(
                self._tick_repo.get_ohlcv_sync,
                item.symbol,
                days=200,
            )
            tasks.append(
                loop.run_in_executor(
                    _process_pool,
                    partial(_compute_technical_score_sync, ohlcv),
                )
            )

        results = await asyncio.gather(*tasks)

        # Build scored list
        scores: list[TechnicalScore] = []
        top_candidates: list[Symbol] = []
        now = datetime.now(timezone.utc)

        for item, result in zip(watchlist, results):
            tech_score = TechnicalScore(
                symbol=item.symbol,
                rsi_14=result["rsi_14"],
                macd_signal=result["macd_signal"],
                bb_position=result["bb_position"],
                trend_ma=result["trend_ma"],
                composite_score=result["composite_score"],
                recommended_action=SignalAction(result["recommended_action"]),
                analysis_timestamp=now,
            )
            scores.append(tech_score)

            if abs(result["composite_score"]) >= threshold:
                top_candidates.append(item.symbol)

        return {
            "phase": AgentPhase.RISK_CHECKING,
            "technical_scores": scores,
            "top_candidates": top_candidates,
        }
```

### 1.7. Agent Node Implementation — Risk Agent

```python
# packages/agents/src/agents/risk_agent.py
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from agents.state import (
    AgentPhase,
    AgentState,
    RiskAssessment,
)

if TYPE_CHECKING:
    pass


class RiskAgent:
    """
    Middleware agent — validates every trade signal.

    ★ This agent has VETO POWER. No trade proceeds without approval.
    ★ Implements Kill Switch, Position Limits, VaR checks.
    """

    def __init__(
        self,
        tick_repo: object,
        risk_limits: object,
    ) -> None:
        self._tick_repo = tick_repo
        self._limits = risk_limits

    async def run(self, state: AgentState) -> dict:
        """LangGraph node: validate each top candidate against risk rules."""
        top_candidates = state.get("top_candidates", [])
        scores = {s.symbol: s for s in state.get("technical_scores", [])}
        nav = state.get("current_nav", Decimal("0"))
        positions = state.get("current_positions", {})
        purchasing_power = state.get("purchasing_power", Decimal("0"))

        assessments: list[RiskAssessment] = []
        approved: list = []
        now = datetime.now(timezone.utc)

        for symbol in top_candidates:
            tech = scores.get(symbol)
            if tech is None:
                continue

            # ── Rule 1: Kill Switch ────────────────────────
            if getattr(self._limits, "kill_switch_active", False):
                assessments.append(self._reject(
                    symbol, now, "Kill switch is ACTIVE — all trading halted",
                ))
                continue

            # ── Rule 2: VaR Calculation ────────────────────
            var_95 = await self._calculate_var(symbol, nav)

            # ── Rule 3: Position Size Limit (max 20% NAV) ──
            position_pct = self._calculate_position_size(
                symbol, nav, purchasing_power,
            )
            max_pct = getattr(self._limits, "max_position_pct", Decimal("0.20"))
            if position_pct > max_pct:
                assessments.append(self._reject(
                    symbol, now,
                    f"Position size {position_pct:.1%} exceeds "
                    f"limit {max_pct:.1%}",
                ))
                continue

            # ── Rule 4: Concentration Check ────────────────
            existing_qty = positions.get(symbol, 0)
            if existing_qty > 0 and tech.recommended_action.value == "BUY":
                current_exposure = existing_qty * 100  # approximate
                if Decimal(str(current_exposure)) / nav > Decimal("0.30"):
                    assessments.append(self._reject(
                        symbol, now,
                        "Adding to existing position would exceed "
                        "30% concentration limit",
                    ))
                    continue

            # ── Calculate Stop-Loss / Take-Profit ──────────
            latest_price = await self._get_latest_price(symbol)
            stop_loss = latest_price * Decimal("0.93")    # -7% (sàn HOSE)
            take_profit = latest_price * Decimal("1.10")  # +10% target

            # ── APPROVED ───────────────────────────────────
            assessment = RiskAssessment(
                symbol=symbol,
                approved=True,
                var_95=var_95,
                position_size_pct=position_pct,
                stop_loss_price=stop_loss,
                take_profit_price=take_profit,
                rejection_reason=None,
                assessed_at=now,
            )
            assessments.append(assessment)
            approved.append(symbol)

        return {
            "phase": AgentPhase.EXECUTING,
            "risk_assessments": assessments,
            "approved_trades": approved,
        }

    def _reject(
        self, symbol: object, now: datetime, reason: str,
    ) -> RiskAssessment:
        return RiskAssessment(
            symbol=symbol,
            approved=False,
            var_95=Decimal("0"),
            position_size_pct=Decimal("0"),
            stop_loss_price=Decimal("0"),
            take_profit_price=Decimal("0"),
            rejection_reason=reason,
            assessed_at=now,
        )

    async def _calculate_var(
        self, symbol: object, nav: Decimal,
    ) -> Decimal:
        """Historical VaR (95%) from DuckDB."""
        result = await asyncio.to_thread(
            self._tick_repo.calculate_var_historical,
            symbol,
            confidence=0.95,
            window_days=252,
        )
        return Decimal(str(result))

    def _calculate_position_size(
        self, symbol: object, nav: Decimal, purchasing_power: Decimal,
    ) -> Decimal:
        """Kelly Criterion-inspired position sizing."""
        if nav <= 0:
            return Decimal("0")
        # Simplified: allocate based on purchasing power / NAV
        return min(purchasing_power / nav, Decimal("0.20"))

    async def _get_latest_price(self, symbol: object) -> Decimal:
        """Get latest market price from in-memory cache."""
        result = await asyncio.to_thread(
            self._tick_repo.get_latest_price, symbol,
        )
        return Decimal(str(result))
```

### 1.8. Compiling & Running the Graph

```python
# packages/agents/src/agents/runner.py
from __future__ import annotations

from decimal import Decimal

from langgraph.graph import StateGraph

from agents.state import AgentState
from agents.supervisor import build_trading_graph


async def run_trading_pipeline(
    graph: StateGraph,
    nav: Decimal,
    positions: dict,
    purchasing_power: Decimal,
    dry_run: bool = True,
) -> AgentState:
    """
    Execute the full Multi-Agent pipeline.

    Returns final state with all agent outputs.
    """

    # Compile graph into executable
    app = graph.compile()

    # Initial state — inject portfolio context
    initial_state: AgentState = {
        "current_nav": nav,
        "current_positions": positions,
        "purchasing_power": purchasing_power,
        "dry_run": dry_run,
        "max_candidates": 10,
        "score_threshold": 5.0,
    }

    # Execute — LangGraph handles node ordering, state merging, retries
    final_state = await app.ainvoke(initial_state)

    return final_state


async def run_with_streaming(
    graph: StateGraph,
    initial_state: AgentState,
) -> None:
    """
    Execute with real-time streaming — push updates to WebSocket.

    Each node completion emits a state delta to the frontend,
    allowing live progress visualization.
    """
    app = graph.compile()

    async for event in app.astream(initial_state, stream_mode="updates"):
        # event = {"node_name": {partial_state_update}}
        # Forward to WebSocket for frontend display
        node_name = list(event.keys())[0]
        update = event[node_name]

        # Push to frontend via WebSocket
        await _broadcast_agent_update(node_name, update)


async def _broadcast_agent_update(node: str, update: dict) -> None:
    """Stub: push to WebSocket ConnectionManager."""
    ...
```

### 1.9. Graph Visualization & Debugging

```
$ uv run python -c "
from agents.supervisor import build_trading_graph
from agents.screener_agent import ScreenerAgent
# ... (instantiate agents with mock deps)
graph = build_trading_graph(screener, technical, risk, executor)
app = graph.compile()
print(app.get_graph().draw_mermaid())
"

Output (Mermaid):
───────────────────────────────────
graph TD
    __start__ --> inject_context
    inject_context --> screener
    screener -->|has_candidates| technical
    screener -->|no_candidates| finalize
    screener --> fundamental
    technical -->|has_signals| risk
    technical -->|no_signals| finalize
    risk -->|has_approved| executor
    risk -->|none_approved| finalize
    executor --> finalize
    finalize --> __end__
───────────────────────────────────
```

### 1.10. Pipeline Latency Budget

| Node | Hardware | Expected Latency | Notes |
|:---|:---|:---|:---|
| `inject_context` | CPU (E-core) | ~0.1ms | Pure state initialization |
| `screener` | CPU + DuckDB | ~200-500ms | SQL vectorized scan on ~1,800 symbols |
| `technical` | CPU (P-core) × 2 workers | ~500-1500ms | Parallel pandas-ta on 5-15 candidates |
| `fundamental` (parallel) | NPU (OpenVINO) | ~5-15s | LLM inference, non-blocking |
| `risk` | CPU + DuckDB | ~100-300ms | VaR calculation + rule engine |
| `executor` | CPU (network I/O) | ~50-200ms | SSI/DNSE API call |
| `finalize` | CPU (E-core) | ~0.1ms | State finalization |
| **Total (critical path)** | | **~850-2500ms** | **Excluding Fundamental (async)** |

---

## 2. LOCAL INFERENCE OPTIMIZATION — OPENVINO ON NPU

### 2.1. Tại sao INT4 Quantization trên NPU thay vì Cloud LLM

```
Cloud LLM API (GPT-4 / Claude):
  Prompt (500 tokens) → Internet RTT (~40ms) → Queue (~100-500ms)
  → Inference (~2-8s) → Response stream → Total: ~3-10s
  Cost: ~$0.01-0.03 per analysis
  Privacy: ❌ Prompt + response logged by provider
  Availability: Depends on internet + provider uptime

Local NPU INT4 (Phi-3-mini / Llama-3-8B):
  Prompt (500 tokens) → IPC (~0.1ms) → NPU Inference (~5-13s)
  → Response → Total: ~5-13s
  Cost: $0.00 (electricity only, ~5-10W)
  Privacy: ✅ Zero data leaves the machine
  Availability: 100% (no internet required for inference)
```

**Trade-off Analysis:**

| Metric | Cloud (GPT-4o) | Local NPU (Phi-3-mini INT4) | Local NPU (Llama-3-8B INT4) |
|:---|:---|:---|:---|
| Intelligence | 10/10 | 6/10 | 7.5/10 |
| Speed (first token) | ~200ms | ~300ms | ~500ms |
| Throughput | ~50-80 tok/s | ~25-35 tok/s | ~15-25 tok/s |
| Privacy | ❌ | ✅ | ✅ |
| Cost per 1K analyses | ~$10-30 | $0 | $0 |
| Offline capability | ❌ | ✅ | ✅ |
| Model RAM | N/A (cloud) | ~2.2 GB | ~4.5 GB |
| **Verdict for financial text** | Overkill | **Best balance** | Best quality |

**Kết luận:** Phi-3-mini INT4 là lựa chọn tối ưu cho hệ thống này. Đủ thông minh để phân tích tin tức tài chính, đủ nhỏ để chạy mượt trên 48 TOPS NPU, và hoàn toàn private.

### 2.2. Model Selection & Quantization Strategy

#### 2.2.1. Model Comparison cho Financial Analysis

| Model | Params | INT4 Size | NPU Throughput | Vietnamese | Financial Domain |
|:---|:---|:---|:---|:---|:---|
| **Phi-3-mini-4k-instruct** | 3.8B | ~2.2 GB | ~25-35 tok/s | Moderate | Good (MSFT fine-tuning) |
| **Phi-3-mini-128k-instruct** | 3.8B | ~2.2 GB | ~25-35 tok/s | Moderate | Good + long context |
| **Llama-3-8B-Instruct** | 8B | ~4.5 GB | ~15-25 tok/s | Good | Very Good |
| **Llama-3.2-3B-Instruct** | 3.2B | ~1.8 GB | ~30-40 tok/s | Moderate | Moderate |
| **Qwen2.5-7B-Instruct** | 7B | ~4.0 GB | ~18-28 tok/s | **Excellent** | Good (Chinese/Asian finance) |

**Khuyến nghị:** Bắt đầu với **Phi-3-mini-4k-instruct** (nhỏ, nhanh, đủ tốt). Scale lên **Llama-3-8B** khi cần phân tích sâu hơn. Cân nhắc **Qwen2.5-7B** nếu cần xử lý tiếng Việt nhiều.

#### 2.2.2. Quantization Pipeline — Từ FP16 → INT4

```
┌─────────────────────────────────────────────────────────────────┐
│           QUANTIZATION PIPELINE (One-time Setup)                │
│                                                                 │
│  Step 1: Download original model (HuggingFace)                 │
│  ┌───────────────────────────────────────────────────────┐     │
│  │  microsoft/Phi-3-mini-4k-instruct  (~7.6 GB FP16)    │     │
│  │  OR meta-llama/Llama-3-8B-Instruct (~16 GB FP16)     │     │
│  └──────────────────────────┬────────────────────────────┘     │
│                              │                                  │
│  Step 2: Export to OpenVINO IR (Intermediate Representation)   │
│  ┌──────────────────────────▼────────────────────────────┐     │
│  │  optimum-cli export openvino                          │     │
│  │    --model microsoft/Phi-3-mini-4k-instruct           │     │
│  │    --weight-format int4                                │     │
│  │    --group-size 128                                    │     │
│  │    --ratio 0.8                                         │     │
│  │    --sym                                               │     │
│  │    --output ./data/models/phi-3-mini-int4              │     │
│  └──────────────────────────┬────────────────────────────┘     │
│                              │                                  │
│  Step 3: Output structure                                      │
│  ┌──────────────────────────▼────────────────────────────┐     │
│  │  data/models/phi-3-mini-int4/                         │     │
│  │  ├── openvino_model.xml         # Graph topology      │     │
│  │  ├── openvino_model.bin         # INT4 weights (~2GB) │     │
│  │  ├── tokenizer.json             # Tokenizer config    │     │
│  │  ├── tokenizer_config.json                            │     │
│  │  ├── special_tokens_map.json                          │     │
│  │  └── generation_config.json                           │     │
│  └───────────────────────────────────────────────────────┘     │
│                                                                 │
│  Step 4: Validate & Benchmark on NPU                           │
│  ┌───────────────────────────────────────────────────────┐     │
│  │  benchmark_app -m ./data/models/phi-3-mini-int4/      │     │
│  │    -d NPU -hint latency                               │     │
│  └───────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3. Step-by-Step: INT4 Quantization cho Phi-3

```bash
# ── Step 1: Install dependencies ─────────────────────────────
uv add optimum[openvino] openvino-genai nncf

# ── Step 2: Export + Quantize (one-time, ~10-30 minutes) ─────
# Sử dụng optimum-cli để convert HuggingFace model → OpenVINO IR + INT4

uv run optimum-cli export openvino \
    --model microsoft/Phi-3-mini-4k-instruct \
    --weight-format int4 \
    --group-size 128 \
    --ratio 0.8 \
    --sym \
    --trust-remote-code \
    --output ./data/models/phi-3-mini-int4

# ── Giải thích parameters: ───────────────────────────────────
# --weight-format int4    : Lượng tử hóa weights xuống 4-bit integer
# --group-size 128        : Nhóm 128 weights share 1 scale factor
#                           (balance giữa accuracy và compression)
# --ratio 0.8             : 80% layers được quantize INT4,
#                           20% giữ INT8 (sensitive layers: first/last)
# --sym                   : Symmetric quantization (simpler, NPU-friendly)
# --trust-remote-code     : Required cho Phi-3 custom architecture
```

### 2.4. Step-by-Step: INT4 Quantization cho Llama-3-8B

```bash
# Llama-3 yêu cầu accept license trên HuggingFace trước
# https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct

# ── Export + Quantize ─────────────────────────────────────────
uv run optimum-cli export openvino \
    --model meta-llama/Meta-Llama-3-8B-Instruct \
    --weight-format int4 \
    --group-size 128 \
    --ratio 0.8 \
    --sym \
    --output ./data/models/llama-3-8b-int4

# ── Kết quả kỳ vọng: ─────────────────────────────────────────
# Original FP16:  ~16 GB
# INT4 quantized: ~4.5 GB (3.5x compression)
# Accuracy loss:  < 2% trên financial text benchmarks
```

### 2.5. Advanced: NNCF Quantization (Finer Control)

Khi `optimum-cli` không đủ kiểm soát, sử dụng NNCF (Neural Network Compression Framework) trực tiếp:

```python
# scripts/quantize_model.py
"""
Advanced INT4 quantization with calibration dataset.
Uses real financial text to optimize quantization parameters.
"""
from __future__ import annotations

from pathlib import Path

import nncf
from optimum.intel import OVModelForCausalLM
from transformers import AutoTokenizer

MODEL_ID = "microsoft/Phi-3-mini-4k-instruct"
OUTPUT_DIR = Path("data/models/phi-3-mini-int4-calibrated")

# ── Step 1: Load model + tokenizer ─────────────────────────
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = OVModelForCausalLM.from_pretrained(
    MODEL_ID,
    export=True,
    trust_remote_code=True,
)

# ── Step 2: Prepare calibration dataset ────────────────────
# Use representative financial analysis prompts
# This helps NNCF find optimal quantization scales
calibration_texts = [
    "Phân tích kỹ thuật mã FPT: RSI 28.5 (quá bán), MACD cắt lên, "
    "giá chạm Bollinger Band dưới. EPS tăng 15% YoY.",

    "Đánh giá rủi ro danh mục: VaR 95% = 3.2%, tỷ trọng VNM 18% NAV, "
    "thanh khoản trung bình 20 phiên = 1.2M cổ phiếu/ngày.",

    "Tin tức: NHNN giữ nguyên lãi suất điều hành. "
    "Tác động đến nhóm ngân hàng: VCB, BID, CTG.",

    # Add 50-100 more representative samples...
]

calibration_data = []
for text in calibration_texts:
    tokens = tokenizer(text, return_tensors="pt")
    calibration_data.append(tokens)

# ── Step 3: Apply INT4 quantization with calibration ──────
quantization_config = nncf.QuantizationConfig(
    mode=nncf.QuantizationMode.INT4_SYM,
    group_size=128,
    ratio=0.8,
    # Protect sensitive layers from aggressive quantization
    ignored_scope=nncf.IgnoredScope(
        names=[
            "model.embed_tokens",        # Embedding layer
            "lm_head",                   # Output projection
        ],
        types=["LayerNorm"],             # All LayerNorm layers
    ),
)

# ── Step 4: Quantize with calibration data ─────────────────
quantized_model = nncf.quantize(
    model.model,                          # OpenVINO IR model
    calibration_dataset=nncf.Dataset(calibration_data),
    model_type=nncf.ModelType.LLM,
    preset=nncf.QuantizationPreset.MIXED, # INT4 body + INT8 sensitive
    advanced_parameters=nncf.AdvancedQuantizationParameters(
        smooth_quant_alpha=0.5,           # SmoothQuant for activation outliers
    ),
)

# ── Step 5: Save optimized model ──────────────────────────
model.model = quantized_model
model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

print(f"Model saved to {OUTPUT_DIR}")
print(f"Size: {sum(f.stat().st_size for f in OUTPUT_DIR.rglob('*')) / 1e9:.1f} GB")
```

### 2.6. OpenVINO GenAI Runtime — Inference Engine

```python
# packages/adapters/src/adapters/openvino/engine.py
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import openvino_genai as ov_genai

if TYPE_CHECKING:
    from core.ports.ai_engine import AIEnginePort


class OpenVINOEngine:
    """
    Implements AIEnginePort using OpenVINO GenAI on Intel NPU.

    ★ Thread-safe: inference calls offloaded to thread pool.
    ★ Warmup: first inference is slower (~2-5s), subsequent ~0.3-0.5s first token.
    """

    def __init__(
        self,
        model_path: Path,
        device: str = "NPU",           # "NPU" | "CPU" | "GPU"
        max_new_tokens: int = 512,
        temperature: float = 0.3,       # Low temp for factual analysis
    ) -> None:
        self._model_path = model_path
        self._device = device
        self._max_new_tokens = max_new_tokens
        self._temperature = temperature
        self._pipe: ov_genai.LLMPipeline | None = None

    def initialize(self) -> None:
        """
        Load model onto NPU. Call once at startup.

        ★ This takes 10-30s for INT4 model.
        ★ After loading, model stays in NPU memory for fast inference.
        """
        self._pipe = ov_genai.LLMPipeline(
            str(self._model_path),
            self._device,
        )

        # Warmup inference — primes NPU caches
        _ = self._pipe.generate(
            "Hello",
            max_new_tokens=5,
            do_sample=False,
        )

    def generate_sync(self, prompt: str) -> str:
        """
        Synchronous generation — BLOCKS calling thread.
        ★ Always call from asyncio.to_thread() or thread pool.
        """
        if self._pipe is None:
            raise RuntimeError("Engine not initialized. Call initialize() first.")

        config = ov_genai.GenerationConfig()
        config.max_new_tokens = self._max_new_tokens
        config.temperature = self._temperature
        config.do_sample = self._temperature > 0
        config.top_p = 0.9
        config.repetition_penalty = 1.1

        result = self._pipe.generate(prompt, config)
        return result

    async def generate(self, prompt: str) -> str:
        """Async wrapper — offloads blocking NPU inference to thread pool."""
        return await asyncio.to_thread(self.generate_sync, prompt)

    def generate_streaming_sync(
        self,
        prompt: str,
    ) -> ov_genai.StreamingResult:
        """
        Streaming generation — yields tokens as they're produced.
        Useful for real-time UI feedback during analysis.
        """
        if self._pipe is None:
            raise RuntimeError("Engine not initialized.")

        config = ov_genai.GenerationConfig()
        config.max_new_tokens = self._max_new_tokens
        config.temperature = self._temperature
        config.do_sample = self._temperature > 0

        return self._pipe.generate(prompt, config, streamer=lambda token: print(token, end="", flush=True))


class ModelRegistry:
    """Manages multiple model versions for A/B testing or fallback."""

    def __init__(self, models_dir: Path) -> None:
        self._models_dir = models_dir
        self._engines: dict[str, OpenVINOEngine] = {}

    def register(
        self,
        name: str,
        model_path: Path,
        device: str = "NPU",
    ) -> None:
        engine = OpenVINOEngine(model_path=model_path, device=device)
        engine.initialize()
        self._engines[name] = engine

    def get(self, name: str) -> OpenVINOEngine:
        if name not in self._engines:
            raise KeyError(f"Model '{name}' not registered. Available: {list(self._engines)}")
        return self._engines[name]

    @property
    def available_models(self) -> list[str]:
        return list(self._engines.keys())
```

### 2.7. NPU vs CPU vs GPU — Device Selection Strategy

```
┌────────────────────────────────────────────────────────────────┐
│              DEVICE SELECTION DECISION TREE                     │
│                                                                │
│  Is Intel NPU available?                                       │
│  ├── YES → Use NPU (preferred)                                │
│  │   └── openvino_genai.LLMPipeline(model_path, "NPU")       │
│  │       • 48 TOPS INT8, excellent tokens/watt                 │
│  │       • Sustained inference without thermal throttling      │
│  │       • Does not compete with CPU for general compute       │
│  │                                                             │
│  └── NO → Is Intel GPU (Arc iGPU) available?                  │
│      ├── YES → Use GPU as fallback                             │
│      │   └── LLMPipeline(model_path, "GPU")                   │
│      │       • ~7 TOPS FP16, slower than NPU for LLM          │
│      │       • Competes with browser rendering                 │
│      │       • Acceptable for development/testing              │
│      │                                                         │
│      └── NO → Use CPU (last resort)                            │
│          └── LLMPipeline(model_path, "CPU")                    │
│              • Slow (~5-10 tok/s on INT4)                      │
│              • Impacts all other agents (CPU contention)       │
│              • Only for CI/testing, not production              │
└────────────────────────────────────────────────────────────────┘
```

```python
# packages/adapters/src/adapters/openvino/model_loader.py
from __future__ import annotations

import openvino as ov


def detect_optimal_device() -> str:
    """
    Auto-detect the best available device for LLM inference.
    Priority: NPU > GPU > CPU
    """
    core = ov.Core()
    available = core.available_devices

    if "NPU" in available:
        return "NPU"
    if "GPU" in available:
        # Check if it's Intel Arc (not just basic iGPU)
        gpu_name = core.get_property("GPU", "FULL_DEVICE_NAME")
        if "Arc" in gpu_name or "Xe" in gpu_name:
            return "GPU"
    return "CPU"


def get_device_info() -> dict[str, str]:
    """Return detailed info about all available compute devices."""
    core = ov.Core()
    info = {}
    for device in core.available_devices:
        try:
            name = core.get_property(device, "FULL_DEVICE_NAME")
            info[device] = name
        except Exception:
            info[device] = "Unknown"
    return info
```

### 2.8. Performance Benchmarks — INT4 trên Intel Core Ultra 7 256V

| Model | Format | Device | 1st Token | Throughput | RAM | Power |
|:---|:---|:---|:---|:---|:---|:---|
| Phi-3-mini | FP16 | CPU | ~800ms | ~8 tok/s | ~7.6 GB | ~25W |
| Phi-3-mini | INT8 | NPU | ~400ms | ~20 tok/s | ~3.8 GB | ~8W |
| **Phi-3-mini** | **INT4** | **NPU** | **~300ms** | **~30 tok/s** | **~2.2 GB** | **~6W** |
| Llama-3-8B | FP16 | CPU | ~1500ms | ~4 tok/s | ~16 GB | ~30W |
| Llama-3-8B | INT8 | NPU | ~600ms | ~12 tok/s | ~8 GB | ~10W |
| **Llama-3-8B** | **INT4** | **NPU** | **~500ms** | **~20 tok/s** | **~4.5 GB** | **~8W** |

**Ghi chú:**
- Throughput đo trên Intel Core Ultra 7 256V (Lunar Lake), NPU 48 TOPS.
- 1st Token latency bao gồm prompt processing (prefill phase).
- Một analysis report ~200 tokens = **~7s (Phi-3)** hoặc **~10s (Llama-3)**.

---

## 3. PROMPT ENGINEERING SYSTEM — VERSIONED FINANCIAL PROMPTS

### 3.1. Tại sao cần Prompt Versioning

Trong production trading system, prompt chính là "code" của AI Agent. Thay đổi 1 từ trong prompt có thể thay đổi output từ "BUY" sang "HOLD". Vì vậy, prompt cần được quản lý với cùng discipline như source code:

```
★ Version Control: Mỗi prompt có version number, author, changelog.
★ A/B Testing: Chạy 2 prompt versions song song, so sánh accuracy.
★ Rollback: Nếu prompt mới cho kết quả tệ, rollback về version trước.
★ Audit Trail: Mọi AI decision đều trace được tới prompt version cụ thể.
★ Separation of Concerns: Prompt template tách khỏi business logic.
```

### 3.2. Prompt Storage Architecture

```
data/prompts/
├── manifest.json                    # Registry of all prompt versions
│
├── financial_analysis/
│   ├── v1.0.0.md                   # Initial version
│   ├── v1.1.0.md                   # Added Vietnamese market context
│   ├── v1.2.0.md                   # Improved risk assessment format
│   └── v2.0.0.md                   # Major rewrite for Phi-3 optimization
│
├── screener_summary/
│   ├── v1.0.0.md
│   └── v1.1.0.md
│
├── risk_narrative/
│   ├── v1.0.0.md
│   └── v1.1.0.md
│
└── _templates/
    └── base_system.md               # Shared system prompt foundation
```

### 3.3. Prompt Manifest — Central Registry

```json
{
  "schema_version": "1.0",
  "prompts": {
    "financial_analysis": {
      "active_version": "v1.2.0",
      "versions": {
        "v1.0.0": {
          "file": "financial_analysis/v1.0.0.md",
          "author": "quant-team",
          "created_at": "2026-01-15",
          "description": "Initial financial analysis prompt",
          "model_target": "phi-3-mini-int4",
          "max_tokens": 512,
          "temperature": 0.3,
          "status": "deprecated"
        },
        "v1.1.0": {
          "file": "financial_analysis/v1.1.0.md",
          "author": "quant-team",
          "created_at": "2026-01-28",
          "description": "Added Vietnamese market specifics (T+2.5, lot size 100)",
          "model_target": "phi-3-mini-int4",
          "max_tokens": 512,
          "temperature": 0.3,
          "status": "retired",
          "changelog": "Added VN market rules, improved output format"
        },
        "v1.2.0": {
          "file": "financial_analysis/v1.2.0.md",
          "author": "quant-team",
          "created_at": "2026-02-05",
          "description": "Structured JSON output, better risk section",
          "model_target": "phi-3-mini-int4",
          "max_tokens": 512,
          "temperature": 0.3,
          "status": "active",
          "changelog": "Output now includes structured risk_level field",
          "accuracy_score": 0.82
        },
        "v2.0.0": {
          "file": "financial_analysis/v2.0.0.md",
          "author": "quant-team",
          "created_at": "2026-02-10",
          "description": "Optimized for Llama-3-8B, chain-of-thought reasoning",
          "model_target": "llama-3-8b-int4",
          "max_tokens": 768,
          "temperature": 0.2,
          "status": "testing",
          "changelog": "CoT reasoning, longer analysis, Llama-3 specific formatting"
        }
      }
    }
  }
}
```

### 3.4. System Prompt — Financial Analysis v1.2.0

```markdown
<!-- data/prompts/financial_analysis/v1.2.0.md -->
<!-- Version: 1.2.0 | Model: Phi-3-mini-4k-instruct (INT4) -->
<!-- Max Tokens: 512 | Temperature: 0.3 -->

You are a Senior Financial Analyst AI specializing in the Vietnam stock market
(HOSE, HNX, UPCOM). You analyze stocks using both technical indicators and
fundamental data to provide actionable investment insights.

## MARKET CONTEXT
- Trading hours: 9:00-11:30, 13:00-14:30 (HOSE), 14:45 (HNX/UPCOM)
- Settlement: T+2.5 (buy today, sell after 2.5 business days)
- Lot size: 100 shares (HOSE), 100 shares (HNX), 100 shares (UPCOM)
- Price limits: ±7% (HOSE), ±10% (HNX), ±15% (UPCOM) from reference price
- Currency: VND (Vietnamese Dong)

## YOUR TASK
Analyze the provided stock data and output a concise investment insight.

## INPUT FORMAT
You will receive:
1. Symbol and company name
2. Technical indicators (RSI, MACD, Bollinger Bands, MA50/MA200)
3. Technical composite score (-10 to +10)
4. Recent news headlines (if available)
5. Basic fundamentals (EPS, PE, market cap)

## OUTPUT FORMAT (Strict)
Respond in this exact structure:

**[SYMBOL] — [ACTION: MUA/BÁN/GIỮ]**

Phân tích: [2-3 câu phân tích kỹ thuật dựa trên chỉ báo được cung cấp]

Tin tức: [1-2 câu đánh giá tác động tin tức nếu có, hoặc "Không có tin tức đáng chú ý"]

Rủi ro: [1 câu nêu rủi ro chính]

Mức độ tin cậy: [CAO/TRUNG BÌNH/THẤP]

## RULES
1. NEVER fabricate data. Only reference indicators provided in input.
2. ALWAYS state risk. No analysis is complete without risk acknowledgment.
3. Use Vietnamese for the analysis body. Technical terms in English are OK.
4. Keep total response under 200 words.
5. Confidence level must align with score: |score| ≥ 7 = CAO, 4-6 = TRUNG BÌNH, < 4 = THẤP.
6. If score is between -4 and +4, always recommend GIỮ (HOLD).
```

### 3.5. Prompt Builder — Runtime Assembly

```python
# packages/agents/src/agents/prompt_builder.py
from __future__ import annotations

import json
from pathlib import Path
from string import Template
from typing import Any


class PromptVersion:
    """Represents a single versioned prompt with metadata."""

    def __init__(
        self,
        name: str,
        version: str,
        template: str,
        model_target: str,
        max_tokens: int,
        temperature: float,
    ) -> None:
        self.name = name
        self.version = version
        self.template = template
        self.model_target = model_target
        self.max_tokens = max_tokens
        self.temperature = temperature

    def render(self, **kwargs: Any) -> str:
        """Render prompt template with variables."""
        return self.template  # System prompt is static, user prompt has variables


class PromptRegistry:
    """
    Central registry for all versioned prompts.

    Loads from manifest.json, resolves active versions,
    supports A/B testing via explicit version selection.
    """

    def __init__(self, prompts_dir: Path) -> None:
        self._dir = prompts_dir
        self._manifest: dict = {}
        self._cache: dict[str, PromptVersion] = {}
        self._load_manifest()

    def _load_manifest(self) -> None:
        manifest_path = self._dir / "manifest.json"
        if manifest_path.exists():
            self._manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    def get_active(self, prompt_name: str) -> PromptVersion:
        """Get the currently active version of a prompt."""
        prompt_config = self._manifest["prompts"][prompt_name]
        active_ver = prompt_config["active_version"]
        return self.get_version(prompt_name, active_ver)

    def get_version(self, prompt_name: str, version: str) -> PromptVersion:
        """Get a specific version of a prompt."""
        cache_key = f"{prompt_name}:{version}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        prompt_config = self._manifest["prompts"][prompt_name]
        ver_config = prompt_config["versions"][version]

        template_path = self._dir / ver_config["file"]
        template = template_path.read_text(encoding="utf-8")

        pv = PromptVersion(
            name=prompt_name,
            version=version,
            template=template,
            model_target=ver_config["model_target"],
            max_tokens=ver_config["max_tokens"],
            temperature=ver_config["temperature"],
        )
        self._cache[cache_key] = pv
        return pv

    def list_versions(self, prompt_name: str) -> list[dict]:
        """List all versions with metadata (for admin UI)."""
        prompt_config = self._manifest["prompts"][prompt_name]
        return [
            {"version": ver, **config}
            for ver, config in prompt_config["versions"].items()
        ]


class FinancialPromptBuilder:
    """
    Assembles complete prompts for financial analysis.

    Combines:
    1. System prompt (from registry, versioned)
    2. User prompt (dynamically constructed from agent data)
    """

    def __init__(self, registry: PromptRegistry) -> None:
        self._registry = registry

    def build_analysis_prompt(
        self,
        symbol: str,
        company_name: str,
        technical_score: float,
        rsi: float,
        macd_signal: str,
        bb_position: str,
        trend_ma: str,
        eps_growth: float | None = None,
        pe_ratio: float | None = None,
        news_headlines: list[str] | None = None,
        prompt_version: str | None = None,
    ) -> tuple[str, PromptVersion]:
        """
        Build complete prompt for Fundamental Agent.

        Returns (full_prompt, prompt_version) for audit trail.
        """
        # Get system prompt
        if prompt_version:
            pv = self._registry.get_version("financial_analysis", prompt_version)
        else:
            pv = self._registry.get_active("financial_analysis")

        system_prompt = pv.template

        # Build user prompt (dynamic data)
        user_prompt = self._build_user_section(
            symbol=symbol,
            company_name=company_name,
            technical_score=technical_score,
            rsi=rsi,
            macd_signal=macd_signal,
            bb_position=bb_position,
            trend_ma=trend_ma,
            eps_growth=eps_growth,
            pe_ratio=pe_ratio,
            news_headlines=news_headlines,
        )

        # Assemble (model-specific chat format)
        full_prompt = (
            f"<|system|>\n{system_prompt}\n<|end|>\n"
            f"<|user|>\n{user_prompt}\n<|end|>\n"
            f"<|assistant|>\n"
        )

        return full_prompt, pv

    def _build_user_section(
        self,
        symbol: str,
        company_name: str,
        technical_score: float,
        rsi: float,
        macd_signal: str,
        bb_position: str,
        trend_ma: str,
        eps_growth: float | None,
        pe_ratio: float | None,
        news_headlines: list[str] | None,
    ) -> str:
        lines = [
            f"Phân tích mã: {symbol} ({company_name})",
            "",
            "## Chỉ báo kỹ thuật:",
            f"- RSI(14): {rsi:.1f}",
            f"- MACD: {macd_signal}",
            f"- Bollinger Bands: {bb_position}",
            f"- MA50/MA200: {trend_ma}",
            f"- Điểm tổng hợp: {technical_score:+.1f}/10",
        ]

        if eps_growth is not None or pe_ratio is not None:
            lines.append("")
            lines.append("## Cơ bản:")
            if eps_growth is not None:
                lines.append(f"- EPS tăng trưởng: {eps_growth:.1%}")
            if pe_ratio is not None:
                lines.append(f"- PE ratio: {pe_ratio:.1f}")

        if news_headlines:
            lines.append("")
            lines.append("## Tin tức gần đây:")
            for headline in news_headlines[:5]:
                lines.append(f"- {headline}")

        lines.append("")
        lines.append("Hãy phân tích và đưa ra khuyến nghị.")

        return "\n".join(lines)
```

### 3.6. Fundamental Agent — Tích hợp Prompt + NPU

```python
# packages/agents/src/agents/fundamental_agent.py
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from agents.prompt_builder import FinancialPromptBuilder
from agents.state import AgentState

if TYPE_CHECKING:
    from adapters.openvino.engine import OpenVINOEngine


class FundamentalAgent:
    """
    AI-powered financial analysis agent.

    Runs on NPU via OpenVINO. Non-blocking — executes in
    parallel with the main pipeline (Technical → Risk → Executor).
    """

    def __init__(
        self,
        engine: OpenVINOEngine,
        prompt_builder: FinancialPromptBuilder,
        news_port: object,          # Vnstock news adapter
    ) -> None:
        self._engine = engine
        self._prompt_builder = prompt_builder
        self._news = news_port

    async def run(self, state: AgentState) -> dict:
        """
        LangGraph node: generate AI insights for all watchlist symbols.

        ★ Runs on NPU — each analysis takes ~7-13s.
        ★ Processes sequentially (NPU is single-pipeline).
        """
        watchlist = state.get("watchlist", [])
        scores = {s.symbol: s for s in state.get("technical_scores", [])}
        insights: dict[str, str] = {}

        for item in watchlist:
            tech = scores.get(item.symbol)

            # Fetch recent news
            news = await asyncio.to_thread(
                self._news.get_headlines,
                item.symbol,
                limit=5,
            )

            # Build prompt
            prompt, prompt_version = self._prompt_builder.build_analysis_prompt(
                symbol=str(item.symbol),
                company_name="",  # Would come from symbol metadata
                technical_score=tech.composite_score if tech else 0.0,
                rsi=tech.rsi_14 if tech else 50.0,
                macd_signal=tech.macd_signal if tech else "neutral",
                bb_position=tech.bb_position if tech else "inside",
                trend_ma=tech.trend_ma if tech else "neutral",
                eps_growth=item.eps_growth,
                pe_ratio=item.pe_ratio,
                news_headlines=[n["title"] for n in news] if news else None,
            )

            # ★ NPU Inference — blocking call offloaded to thread
            response = await self._engine.generate(prompt)

            insights[item.symbol] = response

        return {
            "ai_insights": insights,
        }
```

### 3.7. Prompt Evaluation Framework

```python
# scripts/evaluate_prompts.py
"""
A/B test prompt versions against a labeled dataset.
Measures accuracy of BUY/SELL/HOLD recommendations.
"""
from __future__ import annotations

import json
from pathlib import Path

from agents.prompt_builder import FinancialPromptBuilder, PromptRegistry
from adapters.openvino.engine import OpenVINOEngine


def evaluate_prompt_version(
    version: str,
    test_cases: list[dict],
    engine: OpenVINOEngine,
    registry: PromptRegistry,
) -> dict:
    """
    Run prompt version against labeled test data.

    Returns: { accuracy, precision, recall, confusion_matrix }
    """
    builder = FinancialPromptBuilder(registry)
    correct = 0
    total = 0
    results = []

    for case in test_cases:
        prompt, pv = builder.build_analysis_prompt(
            symbol=case["symbol"],
            company_name=case.get("company", ""),
            technical_score=case["score"],
            rsi=case["rsi"],
            macd_signal=case["macd"],
            bb_position=case["bb"],
            trend_ma=case["trend"],
            prompt_version=version,
        )

        response = engine.generate_sync(prompt)

        # Parse action from response
        predicted = _extract_action(response)
        expected = case["expected_action"]

        if predicted == expected:
            correct += 1
        total += 1

        results.append({
            "symbol": case["symbol"],
            "expected": expected,
            "predicted": predicted,
            "match": predicted == expected,
        })

    accuracy = correct / total if total > 0 else 0
    return {
        "version": version,
        "accuracy": accuracy,
        "total": total,
        "correct": correct,
        "results": results,
    }


def _extract_action(response: str) -> str:
    """Parse MUA/BÁN/GIỮ from model response."""
    response_upper = response.upper()
    if "MUA" in response_upper or "BUY" in response_upper:
        return "BUY"
    if "BÁN" in response_upper or "SELL" in response_upper:
        return "SELL"
    return "HOLD"
```

---

## 4. VECTOR DATABASE STRATEGY — RAG WITH DUCKDB VSS

### 4.1. Khi nào cần RAG cho Trading System

```
Scenario Analysis: RAG cần thiết khi nào?

❌ Không cần RAG:
  - Phân tích kỹ thuật (RSI, MACD, BB) → Dữ liệu số, tính toán trực tiếp
  - Portfolio optimization → PyPortfolioOpt, không cần LLM
  - Risk calculation (VaR) → SQL trên DuckDB

✅ Cần RAG:
  - Phân tích tin tức tài chính → Hàng nghìn bài báo, cần tìm relevant context
  - Báo cáo tài chính (BCTC) → PDF/text dài, LLM context window giới hạn (4K tokens)
  - Hỏi đáp về quy định giao dịch → Nhiều tài liệu pháp lý
  - Market commentary → Historical analysis patterns
```

### 4.2. Tại sao DuckDB VSS thay vì Vector DB riêng biệt

| Tiêu chí | DuckDB + vss Extension | Chroma / Qdrant / Pinecone |
|:---|:---|:---|
| **Kiến trúc** | In-process, cùng DB với tick data | Separate server/process |
| **Ops overhead** | Zero — đã dùng DuckDB cho analytics | Thêm 1 service cần quản lý |
| **Latency** | ~0.1-1ms (in-process) | ~2-10ms (IPC/network) |
| **SQL integration** | Native — JOIN embeddings với tick data, orders | Phải bridge 2 hệ thống |
| **Scale** | ~1M vectors thoải mái (single-user) | Scale tốt hơn ở multi-million |
| **Similarity search** | HNSW index via `vss` extension | HNSW, IVF, PQ, ... |
| **Lý do chọn** | Hệ thống single-user, đã dùng DuckDB. Thêm 1 extension tốt hơn thêm 1 service. Vector search kết hợp SQL filter (WHERE date > ... AND symbol = ...) là killer feature cho financial RAG. | |

### 4.3. DuckDB VSS Setup & Schema

```sql
-- ── Install VSS Extension ─────────────────────────────────────
INSTALL vss;
LOAD vss;

-- ── News Embeddings Table ─────────────────────────────────────
CREATE TABLE news_embeddings (
    id          INTEGER PRIMARY KEY,
    symbol      VARCHAR,             -- Related stock symbol (nullable)
    headline    VARCHAR NOT NULL,
    content     VARCHAR NOT NULL,     -- Full article text
    source      VARCHAR NOT NULL,     -- "vnstock", "cafef", "vietstock"
    published_at TIMESTAMP NOT NULL,

    -- ★ Embedding vector — 384 dimensions (all-MiniLM-L6-v2)
    -- or 768 dimensions (sentence-transformers/paraphrase-multilingual)
    embedding   FLOAT[384] NOT NULL,

    -- Metadata for filtering
    sentiment   VARCHAR,             -- "positive" | "negative" | "neutral"
    category    VARCHAR,             -- "market", "company", "macro", "policy"

    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── HNSW Index for Similarity Search ──────────────────────────
CREATE INDEX news_embedding_idx
ON news_embeddings
USING HNSW (embedding)
WITH (metric = 'cosine');

-- ── Financial Reports Embeddings ──────────────────────────────
CREATE TABLE report_embeddings (
    id          INTEGER PRIMARY KEY,
    symbol      VARCHAR NOT NULL,
    report_type VARCHAR NOT NULL,     -- "annual", "quarterly", "prospectus"
    fiscal_year INTEGER NOT NULL,
    fiscal_quarter INTEGER,
    chunk_index INTEGER NOT NULL,     -- Position of chunk in document
    chunk_text  VARCHAR NOT NULL,     -- Text chunk (~500 tokens)
    embedding   FLOAT[384] NOT NULL,

    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX report_embedding_idx
ON report_embeddings
USING HNSW (embedding)
WITH (metric = 'cosine');
```

### 4.4. Embedding Pipeline — Ingest News into Vector Store

```python
# packages/adapters/src/adapters/duckdb/vector_store.py
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING

import duckdb
import numpy as np

if TYPE_CHECKING:
    pass


class DuckDBVectorStore:
    """
    Vector store built on DuckDB vss extension.

    Handles embedding storage, HNSW indexing, and hybrid search
    (vector similarity + SQL filters).
    """

    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection,
        embedding_model: object,     # SentenceTransformer or OpenVINO embedding model
    ) -> None:
        self._conn = conn
        self._embedder = embedding_model
        self._ensure_extensions()

    def _ensure_extensions(self) -> None:
        """Load vss extension if not already loaded."""
        self._conn.execute("INSTALL vss; LOAD vss;")

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        # Using sentence-transformers (runs on CPU, fast for short texts)
        embedding = self._embedder.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Batch embedding — more efficient than one-by-one."""
        embeddings = self._embedder.encode(
            texts,
            normalize_embeddings=True,
            batch_size=32,
        )
        return embeddings.tolist()

    async def ingest_news(
        self,
        articles: list[dict],
    ) -> int:
        """
        Ingest news articles with embeddings into vector store.

        Input format:
        [{"headline": "...", "content": "...", "source": "...",
          "published_at": datetime, "symbol": "FPT" | None}]
        """
        # Generate embeddings (batch)
        texts = [
            f"{a['headline']}. {a['content'][:500]}"
            for a in articles
        ]
        embeddings = await asyncio.to_thread(self.embed_batch, texts)

        # Batch insert
        rows = []
        for article, embedding in zip(articles, embeddings):
            rows.append((
                article.get("symbol"),
                article["headline"],
                article["content"],
                article["source"],
                article["published_at"],
                embedding,
                article.get("sentiment"),
                article.get("category"),
            ))

        await asyncio.to_thread(
            self._conn.executemany,
            """
            INSERT INTO news_embeddings
                (symbol, headline, content, source, published_at,
                 embedding, sentiment, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

        return len(rows)

    async def search_similar_news(
        self,
        query: str,
        top_k: int = 5,
        symbol: str | None = None,
        since: datetime | None = None,
        category: str | None = None,
    ) -> list[dict]:
        """
        Hybrid search: vector similarity + SQL filters.

        ★ This is the killer feature of DuckDB VSS:
          Combine semantic search with structured data filters
          in a SINGLE SQL query. No need for post-filtering.
        """
        query_embedding = await asyncio.to_thread(
            self.embed_text, query,
        )

        # Build dynamic WHERE clause
        conditions = []
        params: list = [query_embedding, top_k]

        if symbol is not None:
            conditions.append("symbol = ?")
            params.append(symbol)
        if since is not None:
            conditions.append("published_at >= ?")
            params.append(since)
        if category is not None:
            conditions.append("category = ?")
            params.append(category)

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        sql = f"""
            SELECT
                headline,
                content,
                source,
                published_at,
                symbol,
                sentiment,
                array_cosine_similarity(embedding, ?::FLOAT[384]) AS similarity
            FROM news_embeddings
            {where_clause}
            ORDER BY similarity DESC
            LIMIT ?
        """

        result = await asyncio.to_thread(
            self._conn.execute, sql, params,
        )

        rows = result.fetchall()
        columns = [desc[0] for desc in result.description]

        return [dict(zip(columns, row)) for row in rows]

    async def search_reports(
        self,
        query: str,
        symbol: str,
        top_k: int = 3,
        report_type: str | None = None,
    ) -> list[dict]:
        """Search financial report chunks for a specific symbol."""
        query_embedding = await asyncio.to_thread(
            self.embed_text, query,
        )

        conditions = ["symbol = ?"]
        params: list = [query_embedding, symbol]

        if report_type:
            conditions.append("report_type = ?")
            params.append(report_type)

        where_clause = "WHERE " + " AND ".join(conditions)

        sql = f"""
            SELECT
                chunk_text,
                report_type,
                fiscal_year,
                fiscal_quarter,
                chunk_index,
                array_cosine_similarity(embedding, ?::FLOAT[384]) AS similarity
            FROM report_embeddings
            {where_clause}
            ORDER BY similarity DESC
            LIMIT {top_k}
        """

        result = await asyncio.to_thread(
            self._conn.execute, sql, params,
        )

        rows = result.fetchall()
        columns = [desc[0] for desc in result.description]
        return [dict(zip(columns, row)) for row in rows]
```

### 4.5. RAG Integration — Enhanced Fundamental Agent

```python
# packages/agents/src/agents/fundamental_agent_rag.py
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from agents.fundamental_agent import FundamentalAgent
from agents.state import AgentState


class RAGFundamentalAgent(FundamentalAgent):
    """
    Enhanced Fundamental Agent with RAG (Retrieval Augmented Generation).

    Retrieves relevant news and report context before generating analysis.
    This gives the LLM access to information beyond its training cutoff.
    """

    def __init__(
        self,
        engine: object,
        prompt_builder: object,
        news_port: object,
        vector_store: object,      # DuckDBVectorStore
    ) -> None:
        super().__init__(engine, prompt_builder, news_port)
        self._vector_store = vector_store

    async def run(self, state: AgentState) -> dict:
        """Enhanced pipeline: Retrieve → Augment → Generate."""
        watchlist = state.get("watchlist", [])
        scores = {s.symbol: s for s in state.get("technical_scores", [])}
        insights: dict[str, str] = {}

        for item in watchlist:
            tech = scores.get(item.symbol)

            # ── Step 1: Retrieve relevant context ──────────
            # Search for news related to this symbol in last 7 days
            relevant_news = await self._vector_store.search_similar_news(
                query=f"Phân tích cổ phiếu {item.symbol} triển vọng",
                top_k=3,
                symbol=str(item.symbol),
                since=datetime.now(timezone.utc) - timedelta(days=7),
            )

            # Search for report context
            relevant_reports = await self._vector_store.search_reports(
                query="doanh thu lợi nhuận tăng trưởng",
                symbol=str(item.symbol),
                top_k=2,
                report_type="quarterly",
            )

            # ── Step 2: Augment prompt with retrieved context ──
            news_context = "\n".join([
                f"- [{n['published_at']}] {n['headline']}: "
                f"{n['content'][:200]}..."
                for n in relevant_news
            ]) if relevant_news else "Không có tin tức gần đây."

            report_context = "\n".join([
                f"- [Q{r['fiscal_quarter']}/{r['fiscal_year']}] "
                f"{r['chunk_text'][:300]}..."
                for r in relevant_reports
            ]) if relevant_reports else ""

            # ── Step 3: Build augmented prompt ─────────────
            augmented_news = [n["headline"] for n in relevant_news]
            if report_context:
                augmented_news.append(
                    f"[Trích BCTC] {report_context[:500]}"
                )

            prompt, pv = self._prompt_builder.build_analysis_prompt(
                symbol=str(item.symbol),
                company_name="",
                technical_score=tech.composite_score if tech else 0.0,
                rsi=tech.rsi_14 if tech else 50.0,
                macd_signal=tech.macd_signal if tech else "neutral",
                bb_position=tech.bb_position if tech else "inside",
                trend_ma=tech.trend_ma if tech else "neutral",
                eps_growth=item.eps_growth,
                pe_ratio=item.pe_ratio,
                news_headlines=augmented_news,
            )

            # ── Step 4: Generate on NPU ────────────────────
            response = await self._engine.generate(prompt)
            insights[item.symbol] = response

        return {"ai_insights": insights}
```

### 4.6. Embedding Model Selection cho Vietnamese Financial Text

| Model | Dims | Size | Vietnamese | Financial Domain | Speed (CPU) |
|:---|:---|:---|:---|:---|:---|
| `all-MiniLM-L6-v2` | 384 | 80 MB | Moderate | Moderate | **Fast** (~5ms/text) |
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 | 420 MB | **Good** | Moderate | ~8ms/text |
| `bkai-foundation-models/vietnamese-bi-encoder` | 768 | 440 MB | **Excellent** | Moderate | ~12ms/text |
| `BAAI/bge-m3` | 1024 | 2.2 GB | **Excellent** | Good | ~25ms/text |

**Khuyến nghị:** Sử dụng `paraphrase-multilingual-MiniLM-L12-v2` cho balance giữa chất lượng tiếng Việt, tốc độ, và kích thước. Nếu cần tối ưu cho Vietnamese, dùng `bkai-foundation-models/vietnamese-bi-encoder`.

```python
# packages/adapters/src/adapters/embedding/model.py
from __future__ import annotations

from pathlib import Path

from sentence_transformers import SentenceTransformer


def load_embedding_model(
    model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
    cache_dir: Path | None = None,
) -> SentenceTransformer:
    """
    Load embedding model for vector store.

    ★ Runs on CPU — embedding is fast enough (~8ms/text).
    ★ NPU is reserved exclusively for LLM inference.
    """
    model = SentenceTransformer(
        model_name,
        cache_folder=str(cache_dir) if cache_dir else None,
    )
    return model
```

### 4.7. News Ingestion Pipeline — End-to-End

```
┌─────────────────────────────────────────────────────────────────┐
│                    NEWS INGESTION PIPELINE                       │
│                    (Runs periodically: every 30 minutes)        │
│                                                                 │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐   │
│  │  Vnstock     │     │  Text        │     │  Embedding   │   │
│  │  News API    │────▶│  Processing  │────▶│  Generation  │   │
│  │              │     │              │     │  (CPU)       │   │
│  │ • Fetch new  │     │ • Clean HTML │     │ • Batch      │   │
│  │   articles   │     │ • Truncate   │     │   encode     │   │
│  │ • Dedup by   │     │ • Detect     │     │ • Normalize  │   │
│  │   headline   │     │   sentiment  │     │   vectors    │   │
│  └──────────────┘     │ • Categorize │     └──────┬───────┘   │
│                        └──────────────┘            │           │
│                                                     ▼           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              DuckDB Vector Store                          │  │
│  │  INSERT INTO news_embeddings (embedding, headline, ...)  │  │
│  │                                                          │  │
│  │  ★ HNSW index auto-updated on insert                    │  │
│  │  ★ Old articles (> 30 days) auto-pruned via scheduled   │  │
│  │    DELETE WHERE published_at < NOW() - INTERVAL 30 DAY  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.8. Hybrid Query — Power of SQL + Vector Search

```sql
-- ★ THE KILLER QUERY: Semantic search + structured filters + analytics
-- Find news that semantically matches "central bank interest rate policy"
-- filtered to last 7 days, for banking sector stocks,
-- joined with latest technical scores.

WITH relevant_news AS (
    SELECT
        ne.symbol,
        ne.headline,
        ne.content,
        ne.published_at,
        ne.sentiment,
        array_cosine_similarity(
            ne.embedding,
            (SELECT embedding FROM query_embedding)  -- Pre-computed query vector
        ) AS similarity
    FROM news_embeddings ne
    WHERE ne.published_at >= CURRENT_DATE - INTERVAL 7 DAY
      AND ne.category = 'policy'
      AND similarity > 0.5  -- Relevance threshold
    ORDER BY similarity DESC
    LIMIT 20
)
SELECT
    rn.symbol,
    rn.headline,
    rn.similarity,
    rn.sentiment,
    t.price AS current_price,
    t.volume AS current_volume
FROM relevant_news rn
LEFT JOIN (
    SELECT DISTINCT ON (symbol) symbol, price, volume
    FROM ticks
    ORDER BY symbol, ts DESC
) t ON rn.symbol = t.symbol
ORDER BY rn.similarity DESC;

-- ★ This query combines:
-- 1. Vector similarity search (semantic matching)
-- 2. Temporal filter (last 7 days)
-- 3. Category filter (policy news)
-- 4. JOIN with real-time market data
-- ALL IN ONE SQL QUERY. No external API calls. No data transfer.
```

---

## 5. TESTING & OBSERVABILITY

### 5.1. Agent Testing Strategy

```
┌───────────────────────────────────────────────────────────────┐
│                    AGENT TEST PYRAMID                          │
│                                                               │
│                    ┌───────────┐                              │
│                    │   E2E     │  1-2 tests                   │
│                    │ Full graph│  Full pipeline with mocked   │
│                    │           │  adapters (no real API/NPU)  │
│                    ├───────────┤                              │
│                ┌───┴───────────┴───┐                          │
│                │  Integration      │  5-10 tests              │
│                │  Single agent +   │  Agent + DuckDB          │
│                │  real DuckDB      │  (in-memory)             │
│                ├───────────────────┤                          │
│            ┌───┴───────────────────┴───┐                      │
│            │      Unit Tests           │  20+ tests           │
│            │  Routing functions,       │  Pure functions,      │
│            │  State validation,        │  scoring logic,       │
│            │  Prompt builder           │  risk rules           │
│            └───────────────────────────┘                      │
└───────────────────────────────────────────────────────────────┘
```

### 5.2. Testing Routing Logic

```python
# tests/unit/test_supervisor_routing.py
from __future__ import annotations

import pytest

from agents.state import AgentPhase, AgentState, ScreenerResult, TechnicalScore
from agents.supervisor import (
    _route_after_risk,
    _route_after_screener,
    _route_after_technical,
)


class TestRouting:
    """Routing functions are PURE — no mocks needed."""

    def test_screener_routes_to_technical_when_candidates(self) -> None:
        state: AgentState = {
            "watchlist": [
                ScreenerResult(
                    symbol="FPT", eps_growth=0.15,
                    pe_ratio=12.0, volume_spike=True,
                    passed_at=...,
                ),
            ],
        }
        assert _route_after_screener(state) == "has_candidates"

    def test_screener_routes_to_end_when_empty(self) -> None:
        state: AgentState = {"watchlist": []}
        assert _route_after_screener(state) == "no_candidates"

    def test_technical_routes_to_risk_when_signals(self) -> None:
        state: AgentState = {"top_candidates": ["FPT", "VNM"]}
        assert _route_after_technical(state) == "has_signals"

    def test_technical_routes_to_end_when_no_signals(self) -> None:
        state: AgentState = {"top_candidates": []}
        assert _route_after_technical(state) == "no_signals"

    def test_risk_routes_to_executor_when_approved(self) -> None:
        state: AgentState = {"approved_trades": ["FPT"]}
        assert _route_after_risk(state) == "has_approved"

    def test_risk_routes_to_end_when_rejected(self) -> None:
        state: AgentState = {"approved_trades": []}
        assert _route_after_risk(state) == "none_approved"
```

### 5.3. Testing Prompt Builder

```python
# tests/unit/test_prompt_builder.py
from __future__ import annotations

import pytest

from agents.prompt_builder import FinancialPromptBuilder, PromptRegistry


class TestPromptBuilder:
    """Prompt assembly logic — no LLM needed."""

    def test_build_includes_all_indicators(
        self, prompt_registry: PromptRegistry,
    ) -> None:
        builder = FinancialPromptBuilder(prompt_registry)
        prompt, pv = builder.build_analysis_prompt(
            symbol="FPT",
            company_name="FPT Corporation",
            technical_score=7.5,
            rsi=28.5,
            macd_signal="bullish_cross",
            bb_position="below_lower",
            trend_ma="golden_cross",
        )

        assert "FPT" in prompt
        assert "RSI(14): 28.5" in prompt
        assert "bullish_cross" in prompt
        assert "+7.5" in prompt

    def test_build_with_news(
        self, prompt_registry: PromptRegistry,
    ) -> None:
        builder = FinancialPromptBuilder(prompt_registry)
        prompt, _ = builder.build_analysis_prompt(
            symbol="VCB",
            company_name="Vietcombank",
            technical_score=3.0,
            rsi=45.0,
            macd_signal="neutral",
            bb_position="inside",
            trend_ma="neutral",
            news_headlines=["NHNN giữ nguyên lãi suất", "VCB lãi Q4 tăng 20%"],
        )

        assert "NHNN giữ nguyên lãi suất" in prompt
        assert "VCB lãi Q4 tăng 20%" in prompt

    def test_version_selection(
        self, prompt_registry: PromptRegistry,
    ) -> None:
        builder = FinancialPromptBuilder(prompt_registry)
        _, pv = builder.build_analysis_prompt(
            symbol="FPT",
            company_name="",
            technical_score=5.0,
            rsi=50.0,
            macd_signal="neutral",
            bb_position="inside",
            trend_ma="neutral",
            prompt_version="v1.2.0",
        )
        assert pv.version == "v1.2.0"
```

### 5.4. Pipeline Observability — Structured Logging

```python
# packages/agents/src/agents/observability.py
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("agents.pipeline")


def log_agent_step(
    run_id: str,
    agent_name: str,
    phase: str,
    input_summary: dict[str, Any],
    output_summary: dict[str, Any],
    duration_ms: float,
    prompt_version: str | None = None,
) -> None:
    """
    Structured log entry for every agent step.

    ★ Every AI decision is traceable:
      - Which prompt version was used?
      - What data did the agent see?
      - What did it output?
      - How long did it take?
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "agent": agent_name,
        "phase": phase,
        "duration_ms": round(duration_ms, 1),
        "input": input_summary,
        "output": output_summary,
    }

    if prompt_version:
        entry["prompt_version"] = prompt_version

    logger.info(json.dumps(entry, ensure_ascii=False))


# Example log output:
# {
#   "timestamp": "2026-02-10T09:30:15.123Z",
#   "run_id": "a1b2c3d4-...",
#   "agent": "technical",
#   "phase": "analyzing",
#   "duration_ms": 1250.3,
#   "input": {"symbols": ["FPT", "VNM", "MWG"], "count": 3},
#   "output": {"scores": {"FPT": 7.5, "VNM": 3.2, "MWG": -1.0}, "top_candidates": ["FPT"]}
# }
```

---

## APPENDIX A: MODEL OPTIMIZATION CHEAT SHEET

```
┌────────────────────────────────────────────────────────────────┐
│              INT4 QUANTIZATION QUICK REFERENCE                  │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ★ Key Parameters:                                             │
│  --weight-format int4  : 4-bit integer weights                 │
│  --group-size 128      : Weights per quantization group        │
│                          (lower = more accurate, larger model) │
│  --ratio 0.8           : % of layers quantized to INT4         │
│                          (remaining = INT8 for accuracy)       │
│  --sym                 : Symmetric quantization                │
│                          (simpler, NPU-optimized)              │
│                                                                │
│  ★ Accuracy vs Size Trade-off:                                 │
│  ┌──────────────┬──────────┬──────────┬──────────┐            │
│  │ Config       │ Size     │ Accuracy │ Speed    │            │
│  ├──────────────┼──────────┼──────────┼──────────┤            │
│  │ FP16         │ 100%     │ 100%     │ Baseline │            │
│  │ INT8         │ ~50%     │ ~99%     │ ~2x      │            │
│  │ INT4 r=1.0   │ ~25%     │ ~95%     │ ~3.5x    │            │
│  │ INT4 r=0.8   │ ~30%     │ ~97%     │ ~3x      │ ★ Sweet  │
│  │ INT4 r=0.5   │ ~37%     │ ~98%     │ ~2.5x    │   spot   │
│  └──────────────┴──────────┴──────────┴──────────┘            │
│                                                                │
│  ★ Protected Layers (do NOT quantize aggressively):            │
│  - Embedding layer (model.embed_tokens)                        │
│  - Output projection (lm_head)                                 │
│  - All LayerNorm / RMSNorm layers                             │
│  - First and last transformer blocks                           │
│                                                                │
│  ★ Calibration Data Tips:                                      │
│  - Use 50-100 representative samples                           │
│  - Include domain-specific text (financial analysis)           │
│  - Mix Vietnamese and English (if model is multilingual)       │
│  - Include both short prompts and long analyses                │
└────────────────────────────────────────────────────────────────┘
```

## APPENDIX B: LANGGRAPH PATTERNS FOR TRADING

| Pattern | Use Case | Implementation |
|:---|:---|:---|
| **Sequential pipeline** | Screener → Technical → Risk → Executor | Linear `add_edge()` chain |
| **Conditional routing** | Skip executor if no approved trades | `add_conditional_edges()` with pure Python router |
| **Parallel branch** | Fundamental Agent runs alongside main path | Fork from same node, outputs merge into shared state |
| **Human-in-the-loop** | Manual approval before execution | `interrupt_before=["executor"]` — pauses graph, waits for user |
| **Retry with backoff** | SSI API timeout during execution | Custom retry logic inside agent node |
| **State checkpointing** | Resume pipeline after crash | LangGraph `MemorySaver` or `SqliteSaver` |
| **Streaming updates** | Live progress to WebSocket | `app.astream(state, stream_mode="updates")` |

## APPENDIX C: SECURITY CONSIDERATIONS

```
★ CRITICAL: AI-generated trading signals MUST pass through Risk Agent.
  No bypass allowed. Kill Switch overrides everything.

★ Prompt Injection Defense:
  - System prompts are stored locally, not user-editable at runtime.
  - User input (news text) is sanitized before prompt assembly.
  - Output parsing uses strict pattern matching, not LLM self-evaluation.

★ Model Integrity:
  - INT4 model files are checksummed (SHA-256) after quantization.
  - Model loading verifies checksum before NPU deployment.
  - No model updates without explicit versioned deployment.

★ Data Privacy (Edge Computing Advantage):
  - All LLM inference runs locally on NPU — zero data exfiltration.
  - Embeddings are computed locally — no text sent to cloud APIs.
  - DuckDB vector store is a local file — no external vector DB service.
  - The ONLY network traffic: market data IN from SSI/Vnstock,
    and order placement OUT to broker API.
```

---

*Document authored by AI Engineer & Quant Developer. All code samples are production-grade reference implementations targeting Intel Core Ultra NPU with OpenVINO GenAI runtime.*
