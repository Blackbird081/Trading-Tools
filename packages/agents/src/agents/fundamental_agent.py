from __future__ import annotations

import asyncio
import logging
from typing import Any

from agents.guardrails import AgentGuardrailPipeline
from agents.prompt_builder import FinancialPromptBuilder
from agents.state import AgentState

logger = logging.getLogger("agents.fundamental")

_guardrails = AgentGuardrailPipeline()


class FundamentalAgent:
    """AI-powered financial analysis agent.

    Runs on NPU via OpenVINO. Non-blocking — executes in
    parallel with the main pipeline.
    """

    def __init__(
        self,
        engine: Any,
        prompt_builder: FinancialPromptBuilder,
        news_port: Any,
    ) -> None:
        self._engine = engine
        self._prompt_builder = prompt_builder
        self._news = news_port

    async def run(self, state: AgentState) -> dict[str, Any]:
        """LangGraph node: generate AI insights for watchlist symbols."""
        watchlist = state.get("watchlist", [])
        scores = {s.symbol: s for s in state.get("technical_scores", [])}
        insights: dict[str, str] = {}

        for item in watchlist:
            tech = scores.get(item.symbol)

            # Fetch recent news
            news = await self._get_news(item.symbol)

            # Build prompt
            prompt, _pv = self._prompt_builder.build_analysis_prompt(
                symbol=str(item.symbol),
                company_name="",
                technical_score=tech.composite_score if tech else 0.0,
                rsi=tech.rsi_14 if tech else 50.0,
                macd_signal=tech.macd_signal if tech else "neutral",
                bb_position=tech.bb_position if tech else "inside",
                trend_ma=tech.trend_ma if tech else "neutral",
                eps_growth=item.eps_growth,
                pe_ratio=item.pe_ratio,
                news_headlines=news,
            )

            # NPU Inference
            response = await self._generate(prompt)
            insights[str(item.symbol)] = response

        logger.info("Fundamental analysis: %d insights generated", len(insights))
        return {"ai_insights": insights}

    async def _get_news(self, symbol: Any) -> list[str] | None:
        """Fetch news headlines."""
        try:
            if hasattr(self._news, "get_headlines"):
                result = await asyncio.to_thread(
                    self._news.get_headlines,
                    symbol,
                    limit=5,
                )
                if result:
                    raw = [n.get("title", "") for n in result]
                    return _guardrails.sanitize_news_headlines(raw) or None
        except Exception:
            logger.warning("News fetch failed for %s", symbol)
        return None

    async def _generate(self, prompt: str) -> str:
        """Run inference via engine."""
        try:
            if hasattr(self._engine, "generate"):
                result: str = await self._engine.generate(prompt)
                return result
            if hasattr(self._engine, "generate_sync"):
                return await asyncio.to_thread(
                    self._engine.generate_sync,
                    prompt,
                )
        except Exception:
            logger.exception("AI generation failed")
        return "[Analysis unavailable]"
