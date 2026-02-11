from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from agents.screener_agent import ScreenerAgent
from agents.state import AgentPhase, AgentState


@pytest.fixture
def mock_screener() -> AsyncMock:
    screener = AsyncMock()
    screener.screen = AsyncMock(return_value=[])
    return screener


@pytest.fixture
def mock_tick_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.query_volume_spikes = AsyncMock(return_value=[])
    return repo


class TestScreenerAgent:
    @pytest.mark.asyncio
    async def test_empty_screening_returns_empty_watchlist(
        self,
        mock_screener: AsyncMock,
        mock_tick_repo: AsyncMock,
    ) -> None:
        agent = ScreenerAgent(screener_port=mock_screener, tick_repo=mock_tick_repo)
        state: AgentState = {"max_candidates": 10}
        result = await agent.run(state)
        assert result["phase"] == AgentPhase.ANALYZING
        assert result["watchlist"] == []

    @pytest.mark.asyncio
    async def test_screening_returns_candidates(
        self,
        mock_screener: AsyncMock,
        mock_tick_repo: AsyncMock,
    ) -> None:
        mock_screener.screen = AsyncMock(
            return_value=[
                {"symbol": "FPT", "eps_growth": 0.15, "pe_ratio": 12.0},
                {"symbol": "VNM", "eps_growth": 0.20, "pe_ratio": 10.0},
                {"symbol": "MWG", "eps_growth": 0.12, "pe_ratio": 14.0},
            ]
        )
        agent = ScreenerAgent(screener_port=mock_screener, tick_repo=mock_tick_repo)
        state: AgentState = {"max_candidates": 5}
        result = await agent.run(state)
        assert len(result["watchlist"]) == 3
        assert result["watchlist"][0].symbol == "FPT"

    @pytest.mark.asyncio
    async def test_max_candidates_limit(
        self,
        mock_screener: AsyncMock,
        mock_tick_repo: AsyncMock,
    ) -> None:
        candidates = [
            {"symbol": f"SYM{i}", "eps_growth": 0.1, "pe_ratio": 10.0} for i in range(20)
        ]
        mock_screener.screen = AsyncMock(return_value=candidates)
        agent = ScreenerAgent(screener_port=mock_screener, tick_repo=mock_tick_repo)
        state: AgentState = {"max_candidates": 5}
        result = await agent.run(state)
        assert len(result["watchlist"]) == 5

    @pytest.mark.asyncio
    async def test_volume_spike_detected(
        self,
        mock_screener: AsyncMock,
        mock_tick_repo: AsyncMock,
    ) -> None:
        mock_screener.screen = AsyncMock(
            return_value=[
                {"symbol": "FPT", "eps_growth": 0.15, "pe_ratio": 12.0},
            ]
        )
        mock_tick_repo.query_volume_spikes = AsyncMock(return_value=[{"symbol": "FPT"}])
        agent = ScreenerAgent(screener_port=mock_screener, tick_repo=mock_tick_repo)
        state: AgentState = {"max_candidates": 10}
        result = await agent.run(state)
        assert result["watchlist"][0].volume_spike is True

    @pytest.mark.asyncio
    async def test_screener_exception_returns_empty(
        self,
        mock_tick_repo: AsyncMock,
    ) -> None:
        screener = AsyncMock()
        screener.screen = AsyncMock(side_effect=RuntimeError("API down"))
        agent = ScreenerAgent(screener_port=screener, tick_repo=mock_tick_repo)
        state: AgentState = {"max_candidates": 10}
        result = await agent.run(state)
        assert result["watchlist"] == []
