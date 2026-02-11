"""Unit tests for AI insight formatting use case.

Tests:
- Sentiment mapping from score to SignalStrength
- Headline generation
- Recommendation text

Ref: Doc 04 §1.6
"""

from __future__ import annotations

from decimal import Decimal

from core.entities.signal import SignalStrength
from core.use_cases.insight import format_insight


class TestFormatInsight:
    """Tests for format_insight()."""

    def test_strong_buy_sentiment(self) -> None:
        result = format_insight(
            raw_text="FPT shows strong growth potential. Revenue up 30% YoY.",
            sentiment_score=Decimal("0.8"),
            key_factors=["Revenue growth", "PE ratio below sector"],
        )
        assert result.sentiment == SignalStrength.STRONG_BUY
        assert result.confidence == Decimal("0.8")

    def test_buy_sentiment(self) -> None:
        result = format_insight(
            raw_text="Moderate bullish outlook.",
            sentiment_score=Decimal("0.4"),
            key_factors=["Technical support"],
        )
        assert result.sentiment == SignalStrength.BUY

    def test_neutral_sentiment(self) -> None:
        result = format_insight(
            raw_text="Mixed signals. Wait for confirmation.",
            sentiment_score=Decimal("0.0"),
            key_factors=[],
        )
        assert result.sentiment == SignalStrength.NEUTRAL

    def test_sell_sentiment(self) -> None:
        result = format_insight(
            raw_text="Bearish divergence detected.",
            sentiment_score=Decimal("-0.4"),
            key_factors=["MACD bearish cross"],
        )
        assert result.sentiment == SignalStrength.SELL

    def test_strong_sell_sentiment(self) -> None:
        result = format_insight(
            raw_text="Critical risk factors.",
            sentiment_score=Decimal("-0.8"),
            key_factors=["Debt ratio", "Revenue decline"],
        )
        assert result.sentiment == SignalStrength.STRONG_SELL

    def test_headline_from_first_sentence(self) -> None:
        result = format_insight(
            raw_text="FPT shows growth. But risks remain.",
            sentiment_score=Decimal("0.3"),
            key_factors=[],
        )
        assert result.headline == "FPT shows growth"

    def test_headline_truncation(self) -> None:
        long_text = "A" * 200 + ". More text."
        result = format_insight(
            raw_text=long_text,
            sentiment_score=Decimal("0.1"),
            key_factors=[],
        )
        assert len(result.headline) <= 100

    def test_key_points_max_5(self) -> None:
        factors = [f"Factor {i}" for i in range(10)]
        result = format_insight(
            raw_text="Analysis.",
            sentiment_score=Decimal("0.5"),
            key_factors=factors,
        )
        assert len(result.key_points) <= 5

    def test_recommendation_text(self) -> None:
        result = format_insight(
            raw_text="Good outlook.",
            sentiment_score=Decimal("0.8"),
            key_factors=[],
        )
        assert "MUA MẠNH" in result.recommendation
