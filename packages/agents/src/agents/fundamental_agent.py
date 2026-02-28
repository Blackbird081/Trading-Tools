from __future__ import annotations

import asyncio
import logging
from typing import Any

from agents.data_contract import get_value, normalize_financial_data
from agents.dupont_analysis import calculate_extended_dupont
from agents.early_warning import calculate_early_warning
from agents.guardrails import AgentGuardrailPipeline
from agents.industry_analysis.router import get_analysis_description, route_industry
from agents.prompt_builder import FinancialPromptBuilder
from agents.state import AgentState

logger = logging.getLogger("agents.fundamental")

_guardrails = AgentGuardrailPipeline()


class FundamentalAgent:
    """AI-powered financial analysis agent.

    ★ Upgraded: now integrates industry_analysis, early_warning, and DuPont.
    ★ Runs on NPU via OpenVINO. Non-blocking — executes in
      parallel with the main pipeline.
    """

    def __init__(
        self,
        engine: Any,
        prompt_builder: FinancialPromptBuilder,
        news_port: Any,
        financial_data_port: Any = None,  # ★ NEW: optional financial data source
    ) -> None:
        self._engine = engine
        self._prompt_builder = prompt_builder
        self._news = news_port
        self._financial_data = financial_data_port

    async def run(self, state: AgentState) -> dict[str, Any]:
        """LangGraph node: generate AI insights for watchlist symbols.

        ★ Now also runs:
          - Industry-specific analysis (banking/realestate/tech/general)
          - Early Warning System (risk score 0-100)
          - Extended DuPont Analysis (5-component ROE decomposition)
        """
        watchlist = state.get("watchlist", [])
        scores = {s.symbol: s for s in state.get("technical_scores", [])}
        insights: dict[str, str] = {}
        early_warning_results: dict[str, Any] = {}
        industry_analysis_results: dict[str, Any] = {}
        dupont_results: dict[str, Any] = {}

        for item in watchlist:
            symbol_str = str(item.symbol)
            tech = scores.get(item.symbol)

            # Fetch recent news
            news = await self._get_news(item.symbol)

            # ★ Fetch financial data (if port available)
            financial_data = await self._get_financial_data(symbol_str)

            # ★ Run Early Warning System
            ew_result = None
            if financial_data:
                try:
                    ratios = financial_data.get("financial_ratios", {})
                    balance_sheet = financial_data.get("balance_sheet", {})
                    income_statement = financial_data.get("income_statement", {})
                    cash_flow = financial_data.get("cash_flow", {})
                    prev_ratios = financial_data.get("previous_financial_ratios", {})

                    ew_result = calculate_early_warning(
                        financial_ratios=ratios,
                        balance_sheet=balance_sheet,
                        income_statement=income_statement,
                        cash_flow=cash_flow,
                        previous_financial_ratios=prev_ratios,
                        altman_z_score=get_value(ratios, "altman_z_score"),
                        piotroski_f_score=int(get_value(ratios, "piotroski_f_score") or 0) or None,
                    )
                    early_warning_results[symbol_str] = {
                        "risk_score": ew_result.risk_score,
                        "risk_level": ew_result.risk_level,
                        "alerts": ew_result.alerts,
                        "positive_signals": ew_result.positive_signals,
                        "recommendation": ew_result.recommendation,
                        "summary": ew_result.summary,
                    }
                    logger.info(
                        "Early warning for %s: score=%.0f, level=%s",
                        symbol_str, ew_result.risk_score, ew_result.risk_level,
                    )
                except Exception:
                    logger.warning("Early warning failed for %s", symbol_str)

            # ★ Run Industry-Specific Analysis
            if financial_data:
                try:
                    icb_name = financial_data.get("icb_name")
                    icb_code = financial_data.get("icb_code")
                    industry_type = route_industry(icb_name=icb_name, icb_code=icb_code)
                    industry_desc = get_analysis_description(industry_type)

                    industry_metrics = await self._run_industry_analysis(
                        industry_type, financial_data,
                    )
                    industry_analysis_results[symbol_str] = {
                        "industry_type": industry_type,
                        "description": industry_desc,
                        "metrics": industry_metrics,
                    }
                except Exception:
                    logger.warning("Industry analysis failed for %s", symbol_str)

            # ★ Run DuPont Analysis
            if financial_data:
                try:
                    income_statement = financial_data.get("income_statement", {})
                    balance_sheet = financial_data.get("balance_sheet", {})
                    ratios = financial_data.get("financial_ratios", {})

                    dupont = calculate_extended_dupont(
                        income_statement=income_statement,
                        balance_sheet=balance_sheet,
                        financial_ratios=ratios,
                    )
                    dupont_results[symbol_str] = {
                        "roe_computed": dupont.roe_computed,
                        "roe_reported": dupont.roe_reported,
                        "dominant_driver": dupont.dominant_driver,
                        "summary": dupont.summary,
                    }
                except Exception:
                    logger.warning("DuPont analysis failed for %s", symbol_str)

            # Build enhanced prompt with financial analysis context
            early_warning_context = ""
            if ew_result:
                early_warning_context = f"\n\nEarly Warning: {ew_result.summary}"

            dupont_context = ""
            if symbol_str in dupont_results:
                dupont_context = f"\n\nDuPont Analysis:\n{dupont_results[symbol_str]['summary']}"

            prompt, _pv = self._prompt_builder.build_analysis_prompt(
                symbol=symbol_str,
                company_name="",
                technical_score=tech.composite_score if tech else 0.0,
                rsi=tech.rsi_14 if tech else 50.0,
                macd_signal=tech.macd_signal if tech else "neutral",
                bb_position=tech.bb_position if tech else "inside",
                trend_ma=tech.trend_ma if tech else "neutral",
                eps_growth=item.eps_growth,
                pe_ratio=item.pe_ratio,
                news_headlines=news,
                extra_context=early_warning_context + dupont_context,  # ★ NEW
            )

            # NPU Inference
            response = await self._generate(prompt)
            insights[str(item.symbol)] = response

        logger.info("Fundamental analysis: %d insights generated", len(insights))
        return {
            "ai_insights": insights,
            "early_warning_results": early_warning_results,  # ★ NEW
            "industry_analysis_results": industry_analysis_results,  # ★ NEW
            "dupont_results": dupont_results,  # ★ NEW
        }

    async def _get_financial_data(self, symbol: str) -> dict[str, Any] | None:
        """Fetch financial data from port (if available)."""
        if self._financial_data is None:
            return None
        try:
            if hasattr(self._financial_data, "get_financial_data"):
                result = await asyncio.to_thread(
                    self._financial_data.get_financial_data,
                    symbol,
                )
                return result  # type: ignore[no-any-return]
        except Exception:
            logger.warning("Financial data fetch failed for %s", symbol)
        return None

    async def _run_industry_analysis(
        self,
        industry_type: str,
        financial_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Run industry-specific analysis and return metrics dict."""
        from agents.industry_analysis import banking, realestate, technology

        all_data = {
            **financial_data.get("financial_ratios", {}),
            **financial_data.get("balance_sheet", {}),
            **financial_data.get("income_statement", {}),
        }
        # Normalize column names
        normalized = normalize_financial_data(all_data)
        merged = {**all_data, **{k: v for k, v in normalized.items() if v is not None}}

        metrics: dict[str, Any] = {}
        if industry_type == "banking":
            result = banking.analyze_banking(merged)
            metrics = {k: {"value": m.value, "rating": m.rating, "label": m.label} for k, m in result.items()}
        elif industry_type == "realestate":
            result = realestate.analyze_realestate(
                balance_sheet=financial_data.get("balance_sheet", {}),
                income_statement=financial_data.get("income_statement", {}),
            )
            metrics = {k: {"value": m.value, "rating": m.rating, "label": m.label} for k, m in result.items()}
        elif industry_type == "technology":
            revenue_growth = get_value(financial_data.get("financial_ratios", {}), "revenue_growth")
            operating_margin = get_value(financial_data.get("financial_ratios", {}), "operating_margin")
            result = technology.analyze_technology(
                income_statement=financial_data.get("income_statement", {}),
                balance_sheet=financial_data.get("balance_sheet", {}),
                revenue_growth=revenue_growth,
                operating_margin=operating_margin,
            )
            metrics = {k: {"value": m.value, "rating": m.rating, "label": m.label} for k, m in result.items()}

        return metrics

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
