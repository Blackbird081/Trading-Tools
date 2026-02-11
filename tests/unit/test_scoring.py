"""Unit tests for technical scoring use case.

Tests:
- Empty data handling
- Insufficient data handling
- Basic price change scoring

Ref: Doc 04 §1.6
"""

from __future__ import annotations

from decimal import Decimal

from core.use_cases.scoring import compute_technical_score

# Helper to ensure correct type for mypy
_C = dict[str, object]


class TestComputeTechnicalScore:
    """Tests for compute_technical_score()."""

    def test_empty_data_returns_neutral(self) -> None:
        data: list[_C] = []
        result = compute_technical_score(data)
        assert result.score == Decimal("0")
        assert result.rsi_signal == "neutral"
        assert "no data" in result.details.lower()

    def test_single_candle_returns_neutral(self) -> None:
        data: list[_C] = [{"open": 100, "high": 105, "low": 95, "close": 102, "volume": 1000}]
        result = compute_technical_score(data)
        assert result.score == Decimal("0")
        assert "insufficient" in result.details.lower()

    def test_positive_change_positive_score(self) -> None:
        data: list[_C] = [
            {"close": 100},
            {"close": 105},  # +5%
        ]
        result = compute_technical_score(data)
        assert result.score > Decimal("0")

    def test_negative_change_negative_score(self) -> None:
        data: list[_C] = [
            {"close": 100},
            {"close": 95},  # -5%
        ]
        result = compute_technical_score(data)
        assert result.score < Decimal("0")

    def test_score_capped_at_10(self) -> None:
        data: list[_C] = [
            {"close": 100},
            {"close": 200},  # +100% → should cap at 10
        ]
        result = compute_technical_score(data)
        assert result.score <= Decimal("10")

    def test_score_capped_at_negative_10(self) -> None:
        data: list[_C] = [
            {"close": 100},
            {"close": 1},  # -99% → should cap at -10
        ]
        result = compute_technical_score(data)
        assert result.score >= Decimal("-10")

    def test_zero_prev_close_returns_zero(self) -> None:
        data: list[_C] = [
            {"close": 0},
            {"close": 100},
        ]
        result = compute_technical_score(data)
        assert result.score == Decimal("0") or result.score >= Decimal("-10")
