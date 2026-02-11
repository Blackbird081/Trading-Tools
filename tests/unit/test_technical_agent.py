from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from agents.state import AgentPhase, AgentState, ScreenerResult
from agents.technical_agent import TechnicalAgent, compute_indicators
from core.value_objects import Symbol


class TestComputeIndicators:
    def test_empty_data_returns_neutral(self) -> None:
        result = compute_indicators([])
        assert result["composite_score"] == 0.0
        assert result["recommended_action"] == "HOLD"

    def test_single_row_returns_neutral(self) -> None:
        result = compute_indicators([{"close": 100}])
        assert result["composite_score"] == 0.0
        assert result["recommended_action"] == "HOLD"

    def test_two_rows_returns_score(self) -> None:
        data = [{"close": 100}, {"close": 105}]
        result = compute_indicators(data)
        assert "composite_score" in result
        assert "recommended_action" in result


class TestTechnicalAgent:
    @pytest.mark.asyncio
    async def test_empty_watchlist_returns_empty(self) -> None:
        repo = AsyncMock()
        agent = TechnicalAgent(tick_repo=repo)
        state: AgentState = {"watchlist": [], "score_threshold": 5.0}
        result = await agent.run(state)
        assert result["phase"] == AgentPhase.RISK_CHECKING
        assert result["technical_scores"] == []
        assert result["top_candidates"] == []

    @pytest.mark.asyncio
    async def test_agent_scores_watchlist(self) -> None:
        repo = AsyncMock()
        repo.get_ohlcv = AsyncMock(return_value=[{"close": 100}, {"close": 105}])
        agent = TechnicalAgent(tick_repo=repo)
        now = datetime.now(UTC)
        watchlist = [
            ScreenerResult(
                symbol=Symbol("FPT"),
                eps_growth=0.15,
                pe_ratio=12.0,
                volume_spike=True,
                passed_at=now,
            ),
        ]
        state: AgentState = {"watchlist": watchlist, "score_threshold": 5.0}
        result = await agent.run(state)
        assert len(result["technical_scores"]) == 1
        score = result["technical_scores"][0]
        assert score.symbol == Symbol("FPT")
        assert isinstance(score.composite_score, float)

    @pytest.mark.asyncio
    async def test_threshold_filtering(self) -> None:
        repo = AsyncMock()
        repo.get_ohlcv = AsyncMock(
            return_value=[{"close": 100}, {"close": 101}]  # small change -> low score
        )
        agent = TechnicalAgent(tick_repo=repo)
        now = datetime.now(UTC)
        watchlist = [
            ScreenerResult(
                symbol=Symbol("VNM"),
                eps_growth=0.10,
                pe_ratio=10.0,
                volume_spike=False,
                passed_at=now,
            ),
        ]
        state: AgentState = {"watchlist": watchlist, "score_threshold": 5.0}
        result = await agent.run(state)
        # Low score should not be in top_candidates
        assert len(result["top_candidates"]) == 0
