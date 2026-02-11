from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from agents.executor_agent import ExecutorAgent
from agents.risk_agent import RiskAgent
from agents.screener_agent import ScreenerAgent
from agents.state import AgentPhase, AgentState
from agents.supervisor import build_trading_graph
from agents.technical_agent import TechnicalAgent


@pytest.fixture
def mock_screener_port() -> AsyncMock:
    port = AsyncMock()
    port.screen = AsyncMock(
        return_value=[
            {"symbol": "FPT", "eps_growth": 0.15, "pe_ratio": 12.0},
            {"symbol": "VNM", "eps_growth": 0.20, "pe_ratio": 10.0},
        ]
    )
    return port


@pytest.fixture
def mock_tick_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.query_volume_spikes = AsyncMock(return_value=[{"symbol": "FPT"}])
    repo.get_ohlcv = AsyncMock(return_value=[{"close": 90}, {"close": 100}])
    repo.get_latest_price = lambda sym: 100000
    return repo


@pytest.fixture
def risk_limits() -> SimpleNamespace:
    return SimpleNamespace(
        kill_switch_active=False,
        max_position_pct=Decimal("0.20"),
    )


class TestFullPipeline:
    @pytest.mark.asyncio
    async def test_full_pipeline_with_candidates(
        self,
        mock_screener_port: AsyncMock,
        mock_tick_repo: AsyncMock,
        risk_limits: SimpleNamespace,
    ) -> None:
        """Full pipeline: screener finds candidates -> analyze -> risk -> execute."""
        screener = ScreenerAgent(
            screener_port=mock_screener_port,
            tick_repo=mock_tick_repo,
        )
        technical = TechnicalAgent(tick_repo=mock_tick_repo)
        risk = RiskAgent(tick_repo=mock_tick_repo, risk_limits=risk_limits)
        executor = ExecutorAgent()

        graph = build_trading_graph(screener, technical, risk, executor)
        app = graph.compile()

        initial_state: AgentState = {
            "current_nav": Decimal("1000000000"),
            "current_positions": {},
            "purchasing_power": Decimal("100000000"),
            "dry_run": True,
            "max_candidates": 10,
            "score_threshold": 5.0,
        }

        final_state = await app.ainvoke(initial_state)

        # Pipeline should complete
        assert final_state["phase"] == AgentPhase.COMPLETED
        assert "run_id" in final_state
        assert "watchlist" in final_state

    @pytest.mark.asyncio
    async def test_pipeline_empty_screener_skips_to_finalize(
        self,
        mock_tick_repo: AsyncMock,
        risk_limits: SimpleNamespace,
    ) -> None:
        """Empty screener -> finalize (no technical/risk/executor)."""
        empty_screener_port = AsyncMock()
        empty_screener_port.screen = AsyncMock(return_value=[])

        screener = ScreenerAgent(
            screener_port=empty_screener_port,
            tick_repo=mock_tick_repo,
        )
        technical = TechnicalAgent(tick_repo=mock_tick_repo)
        risk = RiskAgent(tick_repo=mock_tick_repo, risk_limits=risk_limits)
        executor = ExecutorAgent()

        graph = build_trading_graph(screener, technical, risk, executor)
        app = graph.compile()

        initial_state: AgentState = {
            "current_nav": Decimal("1000000000"),
            "current_positions": {},
            "purchasing_power": Decimal("100000000"),
            "dry_run": True,
        }

        final_state = await app.ainvoke(initial_state)

        assert final_state["phase"] == AgentPhase.COMPLETED
        assert final_state.get("watchlist") == []
        # Technical, risk, and executor should NOT have run
        assert final_state.get("technical_scores") is None
        assert final_state.get("risk_assessments") is None
        assert final_state.get("execution_plans") is None

    @pytest.mark.asyncio
    async def test_pipeline_kill_switch_rejects_all(
        self,
        mock_screener_port: AsyncMock,
        mock_tick_repo: AsyncMock,
    ) -> None:
        """Kill switch active -> screener finds candidates but risk rejects all."""
        kill_limits = SimpleNamespace(
            kill_switch_active=True,
            max_position_pct=Decimal("0.20"),
        )

        screener = ScreenerAgent(
            screener_port=mock_screener_port,
            tick_repo=mock_tick_repo,
        )
        technical = TechnicalAgent(tick_repo=mock_tick_repo)
        risk = RiskAgent(tick_repo=mock_tick_repo, risk_limits=kill_limits)
        executor = ExecutorAgent()

        graph = build_trading_graph(screener, technical, risk, executor)
        app = graph.compile()

        initial_state: AgentState = {
            "current_nav": Decimal("1000000000"),
            "current_positions": {},
            "purchasing_power": Decimal("100000000"),
            "dry_run": True,
            "max_candidates": 10,
            "score_threshold": 0.1,  # Low threshold so technical passes
        }

        final_state = await app.ainvoke(initial_state)

        assert final_state["phase"] == AgentPhase.COMPLETED
        # Risk should have rejected everything
        if final_state.get("risk_assessments"):
            for assessment in final_state["risk_assessments"]:
                assert assessment.approved is False
