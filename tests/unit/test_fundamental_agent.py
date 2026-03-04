from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
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

    @pytest.mark.asyncio
    async def test_subroles_are_recorded_in_output(
        self,
        mock_engine: AsyncMock,
        mock_news: MagicMock,
        prompt_builder: FinancialPromptBuilder,
    ) -> None:
        financial_data_port = MagicMock()
        financial_data_port.get_financial_data = MagicMock(
            return_value={
                "financial_ratios": {"roe": 0.2, "debt_to_equity": 0.5, "net_margin": 0.15},
                "balance_sheet": {"total_assets": 1_000_000, "total_equity": 500_000},
                "income_statement": {"net_income": 100_000, "revenue": 600_000},
                "cash_flow": {"operating_cash_flow": 120_000},
            }
        )

        agent = FundamentalAgent(
            engine=mock_engine,
            prompt_builder=prompt_builder,
            news_port=mock_news,
            financial_data_port=financial_data_port,
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
        role_payload = result["ai_role_outputs"]["FPT"]
        assert "thesis" in role_payload["active_roles"]
        assert "risk_challenge" in role_payload["active_roles"]
        assert "valuation" in role_payload["active_roles"]

    @pytest.mark.asyncio
    async def test_risk_veto_overrides_action_to_hold(
        self,
        mock_engine: AsyncMock,
        mock_news: MagicMock,
        prompt_builder: FinancialPromptBuilder,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "agents.fundamental_agent.calculate_early_warning",
            lambda **_: SimpleNamespace(
                risk_score=92.0,
                risk_level="critical",
                alerts=["critical leverage"],
                positive_signals=[],
                recommendation="avoid",
                summary="critical risk",
            ),
        )

        financial_data_port = MagicMock()
        financial_data_port.get_financial_data = MagicMock(
            return_value={
                "financial_ratios": {"roe": 0.05, "debt_to_equity": 4.2, "net_margin": 0.01},
                "balance_sheet": {"total_assets": 1_000_000, "total_equity": 100_000},
                "income_statement": {"net_income": 10_000, "revenue": 600_000},
                "cash_flow": {"operating_cash_flow": -10_000},
            }
        )

        agent = FundamentalAgent(
            engine=mock_engine,
            prompt_builder=prompt_builder,
            news_port=mock_news,
            financial_data_port=financial_data_port,
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
        arbitration = result["ai_role_outputs"]["FPT"]["arbitration"]
        assert arbitration["final_action"] == "HOLD"
        assert arbitration["risk_veto"] is True
