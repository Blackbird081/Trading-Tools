from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from agents.risk_agent import RiskAgent
from agents.state import (
    AgentPhase,
    AgentState,
    SignalAction,
    TechnicalScore,
)
from core.value_objects import Symbol


def _make_tech_score(symbol: str, score: float = 7.0) -> TechnicalScore:
    return TechnicalScore(
        symbol=Symbol(symbol),
        rsi_14=35.0,
        macd_signal="bullish_cross",
        bb_position="below_lower",
        trend_ma="golden_cross",
        composite_score=score,
        recommended_action=SignalAction.BUY,
        analysis_timestamp=datetime.now(UTC),
    )


class TestRiskAgent:
    @pytest.mark.asyncio
    async def test_kill_switch_rejects_all(self) -> None:
        repo = AsyncMock()
        limits = SimpleNamespace(kill_switch_active=True, max_position_pct=Decimal("0.20"))
        agent = RiskAgent(tick_repo=repo, risk_limits=limits)
        tech = _make_tech_score("FPT")
        state: AgentState = {
            "top_candidates": [Symbol("FPT")],
            "technical_scores": [tech],
            "current_nav": Decimal("1000000000"),
            "current_positions": {},
            "purchasing_power": Decimal("500000000"),
        }
        result = await agent.run(state)
        assert result["phase"] == AgentPhase.EXECUTING
        assert len(result["approved_trades"]) == 0
        assert result["risk_assessments"][0].rejection_reason == "Kill switch is ACTIVE"

    @pytest.mark.asyncio
    async def test_valid_signal_approved(self) -> None:
        repo = AsyncMock()
        repo.get_latest_price = lambda sym: 100000
        limits = SimpleNamespace(kill_switch_active=False, max_position_pct=Decimal("0.20"))
        agent = RiskAgent(tick_repo=repo, risk_limits=limits)
        tech = _make_tech_score("FPT")
        state: AgentState = {
            "top_candidates": [Symbol("FPT")],
            "technical_scores": [tech],
            "current_nav": Decimal("1000000000"),
            "current_positions": {},
            "purchasing_power": Decimal("100000000"),
        }
        result = await agent.run(state)
        assert len(result["approved_trades"]) == 1
        assert result["risk_assessments"][0].approved is True

    @pytest.mark.asyncio
    async def test_zero_nav_position_size_zero(self) -> None:
        repo = AsyncMock()
        repo.get_latest_price = lambda sym: 100000
        limits = SimpleNamespace(kill_switch_active=False, max_position_pct=Decimal("0.20"))
        agent = RiskAgent(tick_repo=repo, risk_limits=limits)
        tech = _make_tech_score("FPT")
        state: AgentState = {
            "top_candidates": [Symbol("FPT")],
            "technical_scores": [tech],
            "current_nav": Decimal("0"),
            "current_positions": {},
            "purchasing_power": Decimal("0"),
        }
        result = await agent.run(state)
        # With zero NAV, position size is 0 which is <= max 0.20, so it's approved
        assert len(result["approved_trades"]) == 1

    @pytest.mark.asyncio
    async def test_empty_candidates_returns_empty(self) -> None:
        repo = AsyncMock()
        limits = SimpleNamespace(kill_switch_active=False)
        agent = RiskAgent(tick_repo=repo, risk_limits=limits)
        state: AgentState = {
            "top_candidates": [],
            "technical_scores": [],
            "current_nav": Decimal("1000000000"),
            "current_positions": {},
            "purchasing_power": Decimal("500000000"),
        }
        result = await agent.run(state)
        assert len(result["approved_trades"]) == 0
        assert len(result["risk_assessments"]) == 0
