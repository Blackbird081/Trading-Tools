from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, TypedDict

from core.value_objects import Symbol


class AgentPhase(StrEnum):
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
    macd_signal: str
    bb_position: str
    trend_ma: str
    composite_score: float
    recommended_action: SignalAction
    analysis_timestamp: datetime


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    """Output from Risk Management Agent."""

    symbol: Symbol
    approved: bool
    var_95: Decimal
    position_size_pct: Decimal
    latest_price: Decimal       # ★ FIX: actual market price for order entry
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
    order_type: str
    broker: str
    executed: bool
    order_id: str | None
    executed_at: datetime | None


class AgentState(TypedDict, total=False):
    """Shared state for the entire Multi-Agent pipeline."""

    # Pipeline Metadata
    phase: AgentPhase
    run_id: str
    triggered_at: datetime
    error_message: str | None
    # Screener Agent Output
    watchlist: list[ScreenerResult]
    # Technical Agent Output
    technical_scores: list[TechnicalScore]
    top_candidates: list[Symbol]
    # Risk Agent Output
    risk_assessments: list[RiskAssessment]
    approved_trades: list[Symbol]
    # Executor Agent Output
    execution_plans: list[ExecutionPlan]
    # Fundamental Agent Output (Optional)
    ai_insights: dict[Symbol, str]
    # ★ NEW: Financial Analysis Results (baocaotaichinh-inspired)
    early_warning_results: dict[str, Any]   # symbol → EarlyWarningResult.summary
    industry_analysis_results: dict[str, Any]  # symbol → industry metrics dict
    dupont_results: dict[str, Any]          # symbol → DuPontResult summary
    # Portfolio Context
    current_nav: Decimal
    current_positions: dict[Symbol, int]
    purchasing_power: Decimal
    # Configuration
    max_candidates: int
    score_threshold: float
    dry_run: bool
    # ★ FIX: Configurable screener parameters (Sprint 3.3)
    screener_min_eps_growth: float    # default 0.10 (10%)
    screener_max_pe_ratio: float      # default 15.0x
    screener_volume_spike_threshold: float  # default 2.0x average volume
