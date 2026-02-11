from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from agents.executor_agent import ExecutorAgent
from agents.state import (
    AgentState,
    RiskAssessment,
    SignalAction,
    TechnicalScore,
)
from core.value_objects import Symbol


def _make_state(dry_run: bool = True) -> AgentState:
    fpt = Symbol("FPT")
    return AgentState(
        approved_trades=[fpt],
        technical_scores=[
            TechnicalScore(
                symbol=fpt,
                rsi_14=35.0,
                macd_signal="bullish_cross",
                bb_position="below_lower",
                trend_ma="bullish",
                composite_score=7.5,
                recommended_action=SignalAction.BUY,
                analysis_timestamp=datetime.now(UTC),
            )
        ],
        risk_assessments=[
            RiskAssessment(
                symbol=fpt,
                approved=True,
                var_95=Decimal("0.025"),
                position_size_pct=Decimal("0.05"),
                stop_loss_price=Decimal("93000"),
                take_profit_price=Decimal("105000"),
                rejection_reason=None,
                assessed_at=datetime.now(UTC),
            )
        ],
        dry_run=dry_run,
        current_nav=Decimal("1000000000"),
        run_id="test-run-001",
    )


class TestExecutorAgentLive:
    @pytest.mark.asyncio
    async def test_dry_run_no_broker_call(self) -> None:
        broker = AsyncMock()
        agent = ExecutorAgent(broker_port=broker)
        result = await agent.run(_make_state(dry_run=True))
        broker.place_order.assert_not_called()
        assert result["phase"].value == "completed"

    @pytest.mark.asyncio
    async def test_live_order_placed(self) -> None:
        broker = AsyncMock()
        broker.place_order = AsyncMock(return_value="BROKER-001")
        agent = ExecutorAgent(broker_port=broker)
        result = await agent.run(_make_state(dry_run=False))
        broker.place_order.assert_called_once()
        plans = result["execution_plans"]
        assert len(plans) > 0
        assert plans[0].executed is True
        assert plans[0].order_id == "BROKER-001"

    @pytest.mark.asyncio
    async def test_broker_failure_graceful(self) -> None:
        broker = AsyncMock()
        broker.place_order = AsyncMock(side_effect=ConnectionError("API down"))
        agent = ExecutorAgent(broker_port=broker)
        result = await agent.run(_make_state(dry_run=False))
        plans = result["execution_plans"]
        assert len(plans) > 0
        assert plans[0].executed is False
        assert plans[0].order_id is None

    @pytest.mark.asyncio
    async def test_no_broker_configured(self) -> None:
        agent = ExecutorAgent(broker_port=None)
        result = await agent.run(_make_state(dry_run=False))
        plans = result["execution_plans"]
        for plan in plans:
            assert plan.executed is False
