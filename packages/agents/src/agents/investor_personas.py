"""Investor Persona Agents — Inspired by FinceptTerminal's TraderInvestorsAgent.

★ 5 personas adapted for Vietnamese stock market (HOSE/HNX/UPCOM).
★ Each persona has scoring_weights, thresholds, and investment philosophy.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from agents.state import AgentState

logger = logging.getLogger("agents.investor_personas")


class InvestorSignal(StrEnum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    NEUTRAL = "NEUTRAL"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


@dataclass(frozen=True, slots=True)
class PersonaAnalysis:
    persona_id: str
    persona_name: str
    symbol: str
    signal: InvestorSignal
    confidence: Decimal
    composite_score: Decimal
    reasoning: str
    key_factors: tuple[str, ...]
    analyzed_at: datetime


INVESTOR_PERSONAS: dict[str, dict[str, Any]] = {
    "value_investor_vn": {
        "name": "Nhà Đầu Tư Giá Trị VN",
        "thresholds": {"roe_min": 0.15, "debt_to_equity_max": 0.5, "pe_max": 20.0, "bullish_score": 7.5, "bearish_score": 4.0},
        "instructions": "Phân tích theo phong cách Warren Buffett cho thị trường VN. ROE ≥15%, D/E ≤0.5, P/E ≤20x.",
    },
    "growth_investor_vn": {
        "name": "Nhà Đầu Tư Tăng Trưởng VN",
        "thresholds": {"revenue_growth_min": 0.20, "pe_max": 30.0, "bullish_score": 7.0, "bearish_score": 3.5},
        "instructions": "Tìm cổ phiếu tăng trưởng cao VN. Doanh thu ≥20%/năm.",
    },
    "momentum_trader_vn": {
        "name": "Momentum Trader HOSE",
        "thresholds": {"rsi_oversold": 30.0, "rsi_overbought": 70.0, "volume_spike_multiplier": 2.0, "bullish_score": 6.5, "bearish_score": 3.5},
        "instructions": "Giao dịch theo xu hướng kỹ thuật HOSE. RSI, MACD, Volume spike ≥2x.",
    },
    "dividend_investor_vn": {
        "name": "Nhà Đầu Tư Cổ Tức VN",
        "thresholds": {"dividend_yield_min": 0.04, "payout_ratio_max": 0.70, "bullish_score": 7.0, "bearish_score": 4.0},
        "instructions": "Tìm cổ phiếu cổ tức cao VN. Tỷ suất ≥4%, 5 năm liên tiếp.",
    },
    "contrarian_vn": {
        "name": "Nhà Đầu Tư Ngược Chiều VN",
        "thresholds": {"pb_max": 1.0, "rsi_oversold": 25.0, "price_drop_from_high": 0.40, "bullish_score": 7.0, "bearish_score": 4.0},
        "instructions": "Tìm cổ phiếu bị định giá thấp quá mức. P/B ≤1.0, RSI <25.",
    },
}


class InvestorPersonaAgent:
    """Multi-persona investment analysis agent."""

    def __init__(self, engine: Any, personas: list[str] | None = None) -> None:
        self._engine = engine
        self._active_personas = personas or list(INVESTOR_PERSONAS.keys())

    async def run(self, state: AgentState) -> dict[str, Any]:
        watchlist = state.get("watchlist", [])
        technical_scores = {s.symbol: s for s in state.get("technical_scores", [])}
        persona_analyses: dict[str, list[PersonaAnalysis]] = {}
        now = datetime.now(UTC)

        for item in watchlist:
            symbol = item.symbol
            tech = technical_scores.get(symbol)
            analyses: list[PersonaAnalysis] = []

            for persona_id in self._active_personas:
                persona_def = INVESTOR_PERSONAS.get(persona_id)
                if persona_def is None:
                    continue
                score, signal, factors = self._score(persona_id, persona_def, item, tech)
                analyses.append(PersonaAnalysis(
                    persona_id=persona_id, persona_name=persona_def["name"],
                    symbol=str(symbol), signal=signal,
                    confidence=Decimal(str(min(1.0, max(0.0, score / 10.0)))),
                    composite_score=Decimal(str(score)),
                    reasoning=f"Score: {score:.1f}/10",
                    key_factors=tuple(factors), analyzed_at=now,
                ))
            persona_analyses[str(symbol)] = analyses

        consensus = self._aggregate(persona_analyses)
        logger.info("Persona analysis: %d symbols", len(persona_analyses))
        return {"persona_analyses": persona_analyses, "persona_consensus": consensus}

    def _score(self, persona_id: str, persona_def: dict[str, Any], screener_result: Any, technical_score: Any) -> tuple[float, InvestorSignal, list[str]]:
        score = 5.0
        factors: list[str] = []
        thresholds = persona_def.get("thresholds", {})
        eps_growth = float(getattr(screener_result, "eps_growth", 0.0))
        pe_ratio = float(getattr(screener_result, "pe_ratio", 0.0))
        volume_spike = bool(getattr(screener_result, "volume_spike", False))
        rsi = float(getattr(technical_score, "rsi_14", 50.0)) if technical_score else 50.0
        macd = str(getattr(technical_score, "macd_signal", "neutral")) if technical_score else "neutral"

        if persona_id == "momentum_trader_vn":
            if rsi < thresholds.get("rsi_oversold", 30): score += 2.0; factors.append(f"RSI oversold ({rsi:.1f})")
            elif rsi > thresholds.get("rsi_overbought", 70): score -= 2.0; factors.append(f"RSI overbought ({rsi:.1f})")
            if macd == "bullish_cross": score += 2.0; factors.append("MACD bullish cross")
            elif macd == "bearish_cross": score -= 2.0; factors.append("MACD bearish cross")
            if volume_spike: score += 1.5; factors.append("Volume spike")
        elif persona_id in ("value_investor_vn", "dividend_investor_vn"):
            if eps_growth > 0.10: score += 1.5; factors.append(f"EPS growth {eps_growth:.1%}")
            if 0 < pe_ratio < thresholds.get("pe_max", 20.0): score += 1.5; factors.append(f"P/E {pe_ratio:.1f}x")
            elif pe_ratio > thresholds.get("pe_max", 20.0): score -= 1.0
        elif persona_id == "growth_investor_vn":
            if eps_growth >= thresholds.get("revenue_growth_min", 0.20): score += 3.0; factors.append(f"Strong growth {eps_growth:.1%}")
        elif persona_id == "contrarian_vn":
            if rsi < thresholds.get("rsi_oversold", 25.0): score += 3.0; factors.append(f"Extremely oversold RSI ({rsi:.1f})")
            if 0 < pe_ratio < 10.0: score += 2.0; factors.append(f"Very low P/E ({pe_ratio:.1f}x)")

        score = max(0.0, min(10.0, score))
        bullish_t = thresholds.get("bullish_score", 7.0)
        bearish_t = thresholds.get("bearish_score", 4.0)
        if score >= bullish_t: signal = InvestorSignal.STRONG_BUY if score >= 8.5 else InvestorSignal.BUY
        elif score <= bearish_t: signal = InvestorSignal.STRONG_SELL if score <= 2.0 else InvestorSignal.SELL
        else: signal = InvestorSignal.NEUTRAL
        return score, signal, factors

    def _aggregate(self, persona_analyses: dict[str, list[PersonaAnalysis]]) -> dict[str, dict[str, Any]]:
        consensus: dict[str, dict[str, Any]] = {}
        for symbol, analyses in persona_analyses.items():
            if not analyses:
                continue
            signal_counts: dict[str, int] = {}
            total_score = Decimal("0")
            for a in analyses:
                signal_counts[a.signal.value] = signal_counts.get(a.signal.value, 0) + 1
                total_score += a.composite_score
            dominant = max(signal_counts, key=lambda k: signal_counts[k])
            consensus[symbol] = {"dominant_signal": dominant, "agreement_pct": signal_counts[dominant] / len(analyses), "avg_score": float(total_score / len(analyses)), "signal_breakdown": signal_counts}
        return consensus
