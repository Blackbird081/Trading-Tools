from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from agents.fundamental_agent import FundamentalAgent
from agents.prompt_builder import FinancialPromptBuilder, PromptRegistry
from agents.state import AgentState, ScreenerResult
from core.value_objects import Symbol


@pytest.fixture
def mock_engine() -> AsyncMock:
    engine = AsyncMock()
    engine.generate = AsyncMock(return_value="AI insight: BUY recommendation for FPT")
    engine.is_available = True
    return engine


@pytest.fixture
def mock_news() -> MagicMock:
    news = MagicMock()
    news.get_headlines = MagicMock(return_value=[{"title": "FPT tang truong manh"}])
    return news


@pytest.fixture
def prompt_builder(tmp_path: object) -> FinancialPromptBuilder:
    import json
    from pathlib import Path

    p = Path(str(tmp_path))
    manifest = {
        "prompts": {
            "financial_analysis": {
                "active_version": "v1.0.0",
                "versions": {
                    "v1.0.0": {
                        "file": "financial_analysis/v1.0.0.md",
                        "model_target": "phi-3-mini",
                        "max_tokens": 512,
                        "temperature": 0.3,
                    }
                },
            }
        }
    }
    (p / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    fa = p / "financial_analysis"
    fa.mkdir()
    (fa / "v1.0.0.md").write_text("System prompt", encoding="utf-8")
    return FinancialPromptBuilder(PromptRegistry(p))


class TestFundamentalAgent:
    @pytest.mark.asyncio
    async def test_generates_insights(
        self,
        mock_engine: AsyncMock,
        mock_news: MagicMock,
        prompt_builder: FinancialPromptBuilder,
    ) -> None:
        agent = FundamentalAgent(
            engine=mock_engine,
            prompt_builder=prompt_builder,
            news_port=mock_news,
        )
        now = datetime.now(UTC)
        state: AgentState = {
            "watchlist": [
                ScreenerResult(
                    symbol=Symbol("FPT"),
                    eps_growth=0.15,
                    pe_ratio=12.0,
                    volume_spike=True,
                    passed_at=now,
                ),
            ],
            "technical_scores": [],
        }
        result = await agent.run(state)
        assert "ai_insights" in result
        assert "FPT" in str(result["ai_insights"])

    @pytest.mark.asyncio
    async def test_empty_watchlist(
        self,
        mock_engine: AsyncMock,
        mock_news: MagicMock,
        prompt_builder: FinancialPromptBuilder,
    ) -> None:
        agent = FundamentalAgent(
            engine=mock_engine,
            prompt_builder=prompt_builder,
            news_port=mock_news,
        )
        state: AgentState = {"watchlist": [], "technical_scores": []}
        result = await agent.run(state)
        assert result["ai_insights"] == {}

    @pytest.mark.asyncio
    async def test_engine_failure_returns_fallback(
        self,
        mock_news: MagicMock,
        prompt_builder: FinancialPromptBuilder,
    ) -> None:
        engine = AsyncMock()
        engine.generate = AsyncMock(side_effect=RuntimeError("NPU error"))
        agent = FundamentalAgent(
            engine=engine,
            prompt_builder=prompt_builder,
            news_port=mock_news,
        )
        now = datetime.now(UTC)
        state: AgentState = {
            "watchlist": [
                ScreenerResult(
                    symbol=Symbol("FPT"),
                    eps_growth=0.15,
                    pe_ratio=12.0,
                    volume_spike=False,
                    passed_at=now,
                ),
            ],
            "technical_scores": [],
        }
        result = await agent.run(state)
        assert "[Analysis unavailable]" in str(result["ai_insights"].get("FPT", ""))
