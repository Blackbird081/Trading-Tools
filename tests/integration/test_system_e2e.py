from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from agents.executor_agent import ExecutorAgent
from agents.risk_agent import RiskAgent
from agents.screener_agent import ScreenerAgent
from agents.supervisor import build_trading_graph
from agents.technical_agent import TechnicalAgent


class TestFullSystemE2E:
    """End-to-end system test with mocked external dependencies."""

    @pytest.fixture
    def mock_tick_repo(self) -> MagicMock:
        """Mock tick repository with realistic data."""
        repo = MagicMock()

        # Screen candidates
        repo.get_all_symbols = MagicMock(
            return_value=[
                {"symbol": "FPT", "eps_growth": 0.18, "pe_ratio": 14.2},
                {"symbol": "VNM", "eps_growth": 0.05, "pe_ratio": 22.0},
            ]
        )

        # Volume spike data
        repo.get_volume_stats = MagicMock(
            return_value={"FPT": {"avg_20d": 1_000_000, "today": 2_500_000}}
        )

        # OHLCV data — use simple list-based mock to avoid pandas dep
        repo.get_ohlcv = AsyncMock(return_value=[])
        repo.get_ohlcv_sync = MagicMock(return_value=[])

        # Latest price for risk agent
        repo.get_latest_price = MagicMock(return_value=Decimal("102.5"))

        return repo

    @pytest.fixture
    def mock_broker(self) -> AsyncMock:
        broker = AsyncMock()
        broker.place_order = AsyncMock(return_value="BROKER-ORDER-001")
        return broker

    @pytest.mark.asyncio
    async def test_full_pipeline_dry_run(
        self,
        mock_tick_repo: MagicMock,
    ) -> None:
        """Full pipeline in dry-run mode."""
        screener = ScreenerAgent(
            screener_port=MagicMock(), tick_repo=mock_tick_repo,
        )
        technical = TechnicalAgent(tick_repo=mock_tick_repo)
        risk = RiskAgent(tick_repo=mock_tick_repo, risk_limits=MagicMock())
        executor = ExecutorAgent(broker_port=None)

        graph = build_trading_graph(
            screener=screener,
            technical=technical,
            risk=risk,
            executor=executor,
        )
        compiled = graph.compile()

        initial_state: dict[str, object] = {
            "dry_run": True,
            "current_nav": Decimal("1000000000"),
            "current_positions": {},
            "purchasing_power": Decimal("500000000"),
            "max_candidates": 5,
            "score_threshold": 3.0,
        }

        final = await compiled.ainvoke(initial_state)

        # Verify pipeline completed
        assert final.get("phase") is not None
        assert final.get("run_id") is not None

    @pytest.mark.asyncio
    async def test_pipeline_with_live_broker(
        self,
        mock_tick_repo: MagicMock,
        mock_broker: AsyncMock,
    ) -> None:
        """Pipeline with live broker execution."""
        screener = ScreenerAgent(
            screener_port=MagicMock(), tick_repo=mock_tick_repo,
        )
        technical = TechnicalAgent(tick_repo=mock_tick_repo)
        risk = RiskAgent(tick_repo=mock_tick_repo, risk_limits=MagicMock())
        executor = ExecutorAgent(broker_port=mock_broker)

        graph = build_trading_graph(
            screener=screener,
            technical=technical,
            risk=risk,
            executor=executor,
        )
        compiled = graph.compile()

        initial_state: dict[str, object] = {
            "dry_run": False,
            "current_nav": Decimal("1000000000"),
            "current_positions": {},
            "purchasing_power": Decimal("500000000"),
            "max_candidates": 5,
            "score_threshold": 3.0,
        }

        final = await compiled.ainvoke(initial_state)
        assert final.get("phase") is not None

    @pytest.mark.asyncio
    async def test_system_start_command(self) -> None:
        """Verify SystemDependencies can be instantiated."""
        from interface.dependencies import SystemDependencies

        deps = SystemDependencies(config={"model_path": "/nonexistent"})
        await deps.initialize()
        assert deps.get("idempotency_store") is not None
        await deps.shutdown()
