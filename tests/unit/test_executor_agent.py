from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from agents.executor_agent import ExecutorAgent
from agents.state import (
    AgentPhase,
    AgentState,
    RiskAssessment,
    SignalAction,
    TechnicalScore,
)
from core.value_objects import Symbol


def _make_tech(symbol: str) -> TechnicalScore:
    return TechnicalScore(
        symbol=Symbol(symbol),
        rsi_14=35.0,
        macd_signal="bullish_cross",
        bb_position="below_lower",
        trend_ma="golden_cross",
        composite_score=7.0,
        recommended_action=SignalAction.BUY,
        analysis_timestamp=datetime.now(UTC),
    )


def _make_risk(symbol: str) -> RiskAssessment:
    return RiskAssessment(
        symbol=Symbol(symbol),
        approved=True,
        var_95=Decimal("20000000"),
        position_size_pct=Decimal("0.10"),
        latest_price=Decimal("100000"),
        stop_loss_price=Decimal("93000"),
        take_profit_price=Decimal("110000"),
        rejection_reason=None,
        assessed_at=datetime.now(UTC),
    )


class TestExecutorAgent:
    @pytest.mark.asyncio
    async def test_dry_run_not_executed(self) -> None:
        agent = ExecutorAgent()
        state: AgentState = {
            "approved_trades": [Symbol("FPT")],
            "technical_scores": [_make_tech("FPT")],
            "risk_assessments": [_make_risk("FPT")],
            "dry_run": True,
            "current_nav": Decimal("1000000000"),
        }
        result = await agent.run(state)
        assert result["phase"] == AgentPhase.COMPLETED
        assert len(result["execution_plans"]) == 1
        plan = result["execution_plans"][0]
        assert plan.executed is False
        assert plan.order_id is None

    @pytest.mark.asyncio
    async def test_empty_approved_returns_empty(self) -> None:
        agent = ExecutorAgent()
        state: AgentState = {
            "approved_trades": [],
            "technical_scores": [],
            "risk_assessments": [],
            "dry_run": True,
            "current_nav": Decimal("0"),
        }
        result = await agent.run(state)
        assert result["execution_plans"] == []

    @pytest.mark.asyncio
    async def test_hold_signal_skipped(self) -> None:
        agent = ExecutorAgent()
        tech = TechnicalScore(
            symbol=Symbol("VNM"),
            rsi_14=50.0,
            macd_signal="neutral",
            bb_position="inside",
            trend_ma="neutral",
            composite_score=2.0,
            recommended_action=SignalAction.HOLD,
            analysis_timestamp=datetime.now(UTC),
        )
        risk = _make_risk("VNM")
        state: AgentState = {
            "approved_trades": [Symbol("VNM")],
            "technical_scores": [tech],
            "risk_assessments": [risk],
            "dry_run": True,
            "current_nav": Decimal("1000000000"),
        }
        result = await agent.run(state)
        assert len(result["execution_plans"]) == 0
