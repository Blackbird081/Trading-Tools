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

_ROLE_INSTRUCTIONS: dict[str, str] = {
    "thesis": (
        "Role thesis_analyst: summarize core trade thesis in max 3 bullet points "
        "using technical + fundamental context."
    ),
    "valuation": (
        "Role valuation_analyst: evaluate valuation/fundamental quality and state whether "
        "current valuation is attractive, fair, or expensive."
    ),
    "news_catalyst": (
        "Role catalyst_analyst: highlight near-term catalysts and headline risks from recent news."
    ),
    "risk_challenge": (
        "Role risk_challenger: challenge the bullish/bearish thesis, emphasize failure modes, "
        "and provide strict downside warnings."
    ),
}


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
        enable_subroles: bool = True,
    ) -> None:
        self._engine = engine
        self._prompt_builder = prompt_builder
        self._news = news_port
        self._financial_data = financial_data_port
        self._enable_subroles = enable_subroles

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
        ai_role_outputs: dict[str, dict[str, Any]] = {}
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

            try:
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

                role_payload = await self._run_subroles(
                    symbol=symbol_str,
                    base_prompt=prompt,
                    technical_action=(str(tech.recommended_action) if tech else "HOLD"),
                    has_financial_data=financial_data is not None,
                    has_news=bool(news),
                    ew_result=ew_result,
                )
                ai_role_outputs[symbol_str] = role_payload
                insights[symbol_str] = str(role_payload["final_summary"])
            except Exception as exc:
                logger.warning("Prompt/subrole generation failed for %s: %s", symbol_str, exc)
                fallback = (
                    f"{symbol_str}: prompt/subrole configuration unavailable; "
                    "fallback insight only."
                )
                ai_role_outputs[symbol_str] = {
                    "active_roles": [],
                    "role_outputs": {},
                    "arbitration": {"final_action": "HOLD", "risk_veto": False, "policy": "fallback"},
                    "final_summary": fallback,
                }
                insights[symbol_str] = fallback

        logger.info("Fundamental analysis: %d insights generated", len(insights))
        return {
            "ai_insights": insights,
            "ai_role_outputs": ai_role_outputs,
            "early_warning_results": early_warning_results,  # ★ NEW
            "industry_analysis_results": industry_analysis_results,  # ★ NEW
            "dupont_results": dupont_results,  # ★ NEW
        }

    async def _run_subroles(
        self,
        symbol: str,
        base_prompt: str,
        technical_action: str,
        has_financial_data: bool,
        has_news: bool,
        ew_result: Any | None,
    ) -> dict[str, Any]:
        if not self._enable_subroles:
            response = await self._generate(base_prompt)
            return {
                "active_roles": [],
                "role_outputs": {},
                "arbitration": {
                    "final_action": technical_action,
                    "risk_veto": False,
                    "policy": "single-shot",
                },
                "final_summary": response,
            }

        active_roles = self._select_active_roles(has_financial_data=has_financial_data, has_news=has_news)
        role_outputs: dict[str, str] = {}

        for role in active_roles:
            role_prompt = self._build_role_prompt(role=role, base_prompt=base_prompt)
            role_outputs[role] = await self._generate(role_prompt)

        arbitration = self._arbitrate(
            symbol=symbol,
            technical_action=technical_action,
            ew_result=ew_result,
            role_outputs=role_outputs,
        )
        final_summary = self._compose_final_summary(
            symbol=symbol,
            role_outputs=role_outputs,
            arbitration=arbitration,
        )
        return {
            "active_roles": active_roles,
            "role_outputs": role_outputs,
            "arbitration": arbitration,
            "final_summary": final_summary,
        }

    def _select_active_roles(self, has_financial_data: bool, has_news: bool) -> list[str]:
        roles = ["thesis", "risk_challenge"]
        if has_financial_data:
            roles.append("valuation")
        if has_news:
            roles.append("news_catalyst")
        return roles

    def _build_role_prompt(self, role: str, base_prompt: str) -> str:
        instruction = _ROLE_INSTRUCTIONS.get(role, "Role analyst: provide structured analysis.")
        return (
            f"{instruction}\n"
            "Output format:\n"
            "- key_findings: ...\n"
            "- recommendation_bias: BUY/SELL/HOLD\n"
            "- confidence: low/medium/high\n\n"
            f"{base_prompt}"
        )

    def _arbitrate(
        self,
        symbol: str,
        technical_action: str,
        ew_result: Any | None,
        role_outputs: dict[str, str],
    ) -> dict[str, Any]:
        risk_level = str(getattr(ew_result, "risk_level", "")).strip().lower()
        policy = "risk_veto_then_consensus"
        if risk_level in {"critical", "high"}:
            return {
                "final_action": "HOLD",
                "risk_veto": True,
                "risk_level": risk_level,
                "policy": policy,
                "reason": f"Risk veto active ({risk_level})",
            }

        sentiment = 0
        for output in role_outputs.values():
            lower = output.lower()
            if "sell" in lower or "avoid" in lower:
                sentiment -= 1
            if "buy" in lower or "accumulate" in lower:
                sentiment += 1

        base_action = technical_action if technical_action in {"BUY", "SELL", "HOLD"} else "HOLD"
        final_action = base_action
        if base_action == "BUY" and sentiment <= -2:
            final_action = "HOLD"
        if base_action == "SELL" and sentiment >= 2:
            final_action = "HOLD"

        return {
            "final_action": final_action,
            "risk_veto": False,
            "risk_level": risk_level or "low",
            "policy": policy,
            "reason": f"Consensus sentiment score={sentiment}",
            "technical_action": base_action,
        }

    def _compose_final_summary(
        self,
        symbol: str,
        role_outputs: dict[str, str],
        arbitration: dict[str, Any],
    ) -> str:
        lines = [
            f"{symbol}: Final action = {arbitration.get('final_action', 'HOLD')}",
            f"Policy: {arbitration.get('policy', 'n/a')}",
            f"Reason: {arbitration.get('reason', 'n/a')}",
            "Role outputs:",
        ]
        for role, output in role_outputs.items():
            compact = " ".join(output.strip().split())
            lines.append(f"- {role}: {compact[:320]}")
        return "\n".join(lines)

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
