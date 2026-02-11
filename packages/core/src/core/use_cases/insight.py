"""AI insight formatting — structure LLM output for consumption.

★ Pure function: raw AI output → structured AIInsight.
★ No I/O, no LLM calls — formatting only.

Ref: Doc 04 §1.6
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from core.entities.signal import SignalStrength


@dataclass(frozen=True, slots=True)
class InsightSummary:
    """Formatted AI insight for display."""

    headline: str
    sentiment: SignalStrength
    confidence: Decimal
    key_points: tuple[str, ...]
    recommendation: str


def format_insight(
    raw_text: str,
    sentiment_score: Decimal,
    key_factors: list[str],
) -> InsightSummary:
    """Format raw AI analysis into structured insight.

    ★ Pure function — no LLM calls, just formatting.
    ★ Maps sentiment_score to SignalStrength enum.

    Args:
        raw_text: Raw text from LLM analysis.
        sentiment_score: -1.0 (very bearish) to +1.0 (very bullish).
        key_factors: List of key factors from analysis.

    Returns:
        Formatted InsightSummary.
    """
    # Map sentiment score to signal strength
    if sentiment_score >= Decimal("0.6"):
        sentiment = SignalStrength.STRONG_BUY
    elif sentiment_score >= Decimal("0.2"):
        sentiment = SignalStrength.BUY
    elif sentiment_score >= Decimal("-0.2"):
        sentiment = SignalStrength.NEUTRAL
    elif sentiment_score >= Decimal("-0.6"):
        sentiment = SignalStrength.SELL
    else:
        sentiment = SignalStrength.STRONG_SELL

    # Generate headline from raw text (first sentence or first 100 chars)
    headline = raw_text.split(".")[0].strip()
    if len(headline) > 100:
        headline = headline[:97] + "..."

    # Generate recommendation
    recommendation = _generate_recommendation(sentiment)

    return InsightSummary(
        headline=headline,
        sentiment=sentiment,
        confidence=abs(sentiment_score),
        key_points=tuple(key_factors[:5]),  # Top 5 factors
        recommendation=recommendation,
    )


def _generate_recommendation(sentiment: SignalStrength) -> str:
    """Generate human-readable recommendation from sentiment."""
    recommendations: dict[SignalStrength, str] = {
        SignalStrength.STRONG_BUY: "Khuyến nghị MUA MẠNH. Nhiều yếu tố tích cực.",
        SignalStrength.BUY: "Khuyến nghị MUA. Tín hiệu tích cực.",
        SignalStrength.NEUTRAL: "TRUNG LẬP. Cần theo dõi thêm.",
        SignalStrength.SELL: "Khuyến nghị BÁN. Tín hiệu tiêu cực.",
        SignalStrength.STRONG_SELL: "Khuyến nghị BÁN MẠNH. Nhiều rủi ro.",
    }
    return recommendations.get(sentiment, "Không đủ dữ liệu để đánh giá.")
