"""Risk entities — risk metrics, limits, and VaR results.

Ref: Doc 02 §2.2, Doc 05 §3.6
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class RiskLimit:
    """Configurable risk limits — enforced by Risk Agent.

    ★ max_position_pct: Maximum single order as % of NAV.
    ★ max_daily_loss: Daily loss limit (absolute VND).
    ★ kill_switch_active: Emergency halt — blocks ALL trading.
    ★ stop_loss_pct: Stop-loss distance below entry price (default 5%).
    ★ take_profit_pct: Take-profit distance above entry price (default 15%).
    """

    max_position_pct: Decimal  # e.g., 0.20 = 20% of NAV per order
    max_daily_loss: Decimal  # Maximum acceptable daily loss (VND)
    kill_switch_active: bool  # Emergency halt switch
    # ★ FIX: Configurable stop-loss/take-profit (not hardcoded ±7%/±10%)
    stop_loss_pct: Decimal = Decimal("0.05")    # 5% below entry (not 7% = HOSE floor)
    take_profit_pct: Decimal = Decimal("0.15")  # 15% above entry


@dataclass(frozen=True, slots=True)
class RiskMetrics:
    """Portfolio-level risk snapshot."""

    total_exposure: Decimal  # Sum of all position market values
    daily_pnl: Decimal  # Today's realized + unrealized PnL
    max_drawdown: Decimal  # Worst peak-to-trough decline
    sharpe_ratio: Decimal | None  # Risk-adjusted return (needs history)
    calculated_at: datetime


@dataclass(frozen=True, slots=True)
class VaRResult:
    """Value at Risk calculation result.

    ★ Historical VaR using DuckDB ASOF JOIN for time-aligned data.
    """

    confidence_level: Decimal  # e.g., 0.95 = 95% VaR
    holding_period_days: int
    var_amount: Decimal  # Max expected loss at confidence level
    method: str  # "historical" | "parametric"
    sample_size: int  # Number of historical data points used
    calculated_at: datetime
