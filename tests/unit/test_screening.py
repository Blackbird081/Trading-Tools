"""Unit tests for screening use case.

Tests:
- Empty candidates
- Volume filter
- Price filter
- Exchange filter

Ref: Doc 02 §2.4
"""

from __future__ import annotations

from decimal import Decimal

from core.use_cases.screening import ScreeningCriteria, run_screening


class TestRunScreening:
    """Tests for run_screening()."""

    def test_empty_candidates(self) -> None:
        criteria = ScreeningCriteria()
        result = run_screening([], criteria)
        assert result.total_scanned == 0
        assert result.total_matched == 0
        assert len(result.symbols) == 0

    def test_filters_by_exchange(self) -> None:
        candidates = [
            {"symbol": "FPT", "exchange": "HOSE", "price": 98500, "volume": 200000},
            {"symbol": "ACB", "exchange": "HNX", "price": 30000, "volume": 200000},
        ]
        criteria = ScreeningCriteria(exchanges=("HOSE",))
        result = run_screening(candidates, criteria)
        assert result.total_matched == 1
        assert result.symbols[0] == "FPT"

    def test_filters_by_volume(self) -> None:
        candidates = [
            {"symbol": "FPT", "exchange": "HOSE", "price": 98500, "volume": 200000},
            {"symbol": "LOW", "exchange": "HOSE", "price": 50000, "volume": 50000},
        ]
        criteria = ScreeningCriteria(min_volume=100000)
        result = run_screening(candidates, criteria)
        assert result.total_matched == 1
        assert result.symbols[0] == "FPT"

    def test_filters_by_price_range(self) -> None:
        candidates = [
            {"symbol": "CHEAP", "exchange": "HOSE", "price": 1000, "volume": 200000},
            {"symbol": "FPT", "exchange": "HOSE", "price": 98500, "volume": 200000},
            {"symbol": "EXP", "exchange": "HOSE", "price": 600000, "volume": 200000},
        ]
        criteria = ScreeningCriteria(
            min_price=Decimal("5000"),
            max_price=Decimal("500000"),
        )
        result = run_screening(candidates, criteria)
        assert result.total_matched == 1
        assert result.symbols[0] == "FPT"

    def test_all_filters_combined(self) -> None:
        candidates = [
            {"symbol": "GOOD", "exchange": "HOSE", "price": 50000, "volume": 200000},
            {"symbol": "BAD1", "exchange": "HNX", "price": 50000, "volume": 200000},
            {"symbol": "BAD2", "exchange": "HOSE", "price": 50000, "volume": 50000},
            {"symbol": "BAD3", "exchange": "HOSE", "price": 1000, "volume": 200000},
        ]
        criteria = ScreeningCriteria(
            min_volume=100000,
            min_price=Decimal("5000"),
            max_price=Decimal("500000"),
            exchanges=("HOSE",),
        )
        result = run_screening(candidates, criteria)
        assert result.total_scanned == 4
        assert result.total_matched == 1
        assert result.symbols[0] == "GOOD"
