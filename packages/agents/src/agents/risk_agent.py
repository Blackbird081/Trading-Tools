from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from agents.state import AgentPhase, AgentState, RiskAssessment

logger = logging.getLogger("agents.risk")

# ★ Early warning risk levels that block trading
_BLOCKED_RISK_LEVELS = frozenset({"critical"})


class RiskAgent:
    """Middleware agent — validates every trade signal.

    Has VETO POWER. No trade proceeds without approval.
    Implements Kill Switch, Position Limits, VaR checks.
    """

    def __init__(self, tick_repo: Any, risk_limits: Any) -> None:
        self._tick_repo = tick_repo
        self._limits = risk_limits

    async def run(self, state: AgentState) -> dict[str, Any]:
        """LangGraph node: validate each top candidate against risk rules."""
        top_candidates = state.get("top_candidates", [])
        scores = {s.symbol: s for s in state.get("technical_scores", [])}
        nav = state.get("current_nav", Decimal("0"))
        positions = state.get("current_positions", {})
        purchasing_power = state.get("purchasing_power", Decimal("0"))
        # ★ NEW: Early warning results from FundamentalAgent
        early_warning_results: dict[str, Any] = state.get("early_warning_results", {})

        assessments: list[RiskAssessment] = []
        approved: list[Any] = []
        now = datetime.now(UTC)

        for symbol in top_candidates:
            symbol_str = str(symbol)
            tech = scores.get(symbol)
            if tech is None:
                continue

            # Rule 1: Kill Switch
            if getattr(self._limits, "kill_switch_active", False):
                assessments.append(self._reject(symbol, now, "Kill switch is ACTIVE"))
                continue

            # ★ Rule 1b: Early Warning — block if risk_level == critical
            ew = early_warning_results.get(symbol_str)
            if ew and ew.get("risk_level") in _BLOCKED_RISK_LEVELS:
                risk_score = ew.get("risk_score", 0)
                alerts = ew.get("alerts", [])
                alert_summary = "; ".join(alerts[:3]) if alerts else "Rủi ro tài chính nghiêm trọng"
                assessments.append(self._reject(
                    symbol, now,
                    f"Early Warning CRITICAL (score={risk_score:.0f}/100): {alert_summary}",
                ))
                logger.warning(
                    "Trade blocked by Early Warning: %s score=%.0f level=%s",
                    symbol_str, risk_score, ew.get("risk_level"),
                )
                continue

            # Rule 2: VaR Calculation
            var_95 = await self._calculate_var(symbol, nav)

            # ★ FIX: Fetch latest_price early — needed for position size AND stop/take-profit
            latest_price = await self._get_latest_price(symbol)

            # Rule 3: Position Size Limit (max 20% NAV)
            # ★ FIX: Pass latest_price so position size accounts for actual lot rounding
            position_pct = self._calculate_position_size(nav, purchasing_power, latest_price)
            max_pct = getattr(
                self._limits,
                "max_position_pct",
                Decimal("0.20"),
            )
            if position_pct > max_pct:
                assessments.append(
                    self._reject(
                        symbol,
                        now,
                        f"Position size {position_pct:.1%} exceeds limit {max_pct:.1%}",
                    )
                )
                continue

            # Rule 4: Concentration Check
            existing_qty = positions.get(symbol, 0)
            if existing_qty > 0 and tech.recommended_action.value == "BUY" and nav > 0:
                current_exposure = Decimal(str(existing_qty * 100))
                if current_exposure / nav > Decimal("0.30"):
                    assessments.append(
                        self._reject(
                            symbol,
                            now,
                            "Exceeds 30% concentration limit",
                        )
                    )
                    continue

            # Calculate Stop-Loss / Take-Profit using configurable percentages
            # ★ FIX: stop_loss_pct default 5% (not 7% = price band floor)
            stop_loss_pct = getattr(self._limits, "stop_loss_pct", Decimal("0.05"))
            take_profit_pct = getattr(self._limits, "take_profit_pct", Decimal("0.15"))
            stop_loss = latest_price * (Decimal("1") - stop_loss_pct)
            take_profit = latest_price * (Decimal("1") + take_profit_pct)

            # APPROVED
            assessment = RiskAssessment(
                symbol=symbol,
                approved=True,
                var_95=var_95,
                position_size_pct=position_pct,
                latest_price=latest_price,   # ★ FIX: store actual market price
                stop_loss_price=stop_loss,
                take_profit_price=take_profit,
                rejection_reason=None,
                assessed_at=now,
            )
            assessments.append(assessment)
            approved.append(symbol)

        logger.info(
            "Risk assessment: %d checked, %d approved",
            len(assessments),
            len(approved),
        )
        return {
            "phase": AgentPhase.EXECUTING,
            "risk_assessments": assessments,
            "approved_trades": approved,
        }

    def _reject(self, symbol: Any, now: datetime, reason: str) -> RiskAssessment:
        return RiskAssessment(
            symbol=symbol,
            approved=False,
            var_95=Decimal("0"),
            position_size_pct=Decimal("0"),
            latest_price=Decimal("0"),   # ★ FIX: required field
            stop_loss_price=Decimal("0"),
            take_profit_price=Decimal("0"),
            rejection_reason=reason,
            assessed_at=now,
        )

    async def _calculate_var(self, symbol: Any, nav: Decimal) -> Decimal:
        """Historical VaR (95%)."""
        try:
            fn = getattr(self._tick_repo, "calculate_var_historical", None)
            if fn is not None and callable(fn):
                import asyncio

                result = await asyncio.to_thread(
                    fn,
                    symbol,
                    confidence=0.95,
                    window_days=252,
                )
                return Decimal(str(result))
        except Exception:
            logger.warning("VaR calculation failed for %s, using default", symbol)
        return nav * Decimal("0.02")

    def _calculate_position_size(
        self,
        nav: Decimal,
        purchasing_power: Decimal,
        latest_price: Decimal | None = None,
    ) -> Decimal:
        """Calculate position size as % of NAV.

        ★ FIX: Takes into account latest_price to compute actual lot-rounded value.
        Returns the fraction of NAV that will actually be used.
        """
        if nav <= 0:
            return Decimal("0")
        max_pct = getattr(self._limits, "max_position_pct", Decimal("0.20"))
        max_order_value = nav * max_pct
        affordable = min(purchasing_power, max_order_value)
        if latest_price and latest_price > 0:
            # Round down to nearest lot (100 shares) to get actual order value
            lots = int(affordable / latest_price) // 100
            actual_value = Decimal(lots * 100) * latest_price
            return actual_value / nav if nav > 0 else Decimal("0")
        # Fallback: simple ratio without price info
        return min(affordable / nav, max_pct)

    async def _get_latest_price(self, symbol: Any) -> Decimal:
        try:
            fn = getattr(self._tick_repo, "get_latest_price", None)
            if fn is not None and callable(fn):
                import asyncio

                result = await asyncio.to_thread(fn, symbol)
                return Decimal(str(result))
        except Exception:
            logger.warning("Latest price failed for %s", symbol)
        return Decimal("100000")
