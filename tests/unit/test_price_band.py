"""Unit tests for price_band use case.

Tests:
- Ceiling/floor calculation for HOSE (±7%), HNX (±10%), UPCOM (±15%)
- Tick size rules (HOSE: 10/50/100 VND)
- Price validation within/outside band
- Tick size alignment validation

Ref: Doc 05 §5.3
"""

from __future__ import annotations

from decimal import Decimal

from core.entities.tick import Exchange
from core.use_cases.price_band import (
    PriceBand,
    calculate_price_band,
    validate_order_price,
)
from core.value_objects import Price, Symbol


class TestCalculatePriceBand:
    """Tests for calculate_price_band()."""

    def test_hose_7_percent_band(self) -> None:
        """HOSE: ±7% price band."""
        band = calculate_price_band(Symbol("FPT"), Exchange.HOSE, Price(Decimal("100000")))
        assert band.exchange == Exchange.HOSE
        # Ceiling = 100000 * 1.07 = 107000, snap down = 107000
        assert band.ceiling_price <= Price(Decimal("107000"))
        # Floor = 100000 * 0.93 = 93000, snap up = 93000
        assert band.floor_price >= Price(Decimal("93000"))
        assert band.tick_size == Decimal("100")  # Price >= 50000

    def test_hnx_10_percent_band(self) -> None:
        """HNX: ±10% price band."""
        band = calculate_price_band(Symbol("ACB"), Exchange.HNX, Price(Decimal("30000")))
        # Ceiling = 30000 * 1.10 = 33000
        assert band.ceiling_price <= Price(Decimal("33000"))
        # Floor = 30000 * 0.90 = 27000
        assert band.floor_price >= Price(Decimal("27000"))
        assert band.tick_size == Decimal("100")  # HNX: fixed 100

    def test_upcom_15_percent_band(self) -> None:
        """UPCOM: ±15% price band."""
        band = calculate_price_band(Symbol("XXX"), Exchange.UPCOM, Price(Decimal("20000")))
        # Ceiling = 20000 * 1.15 = 23000
        assert band.ceiling_price <= Price(Decimal("23000"))
        # Floor = 20000 * 0.85 = 17000
        assert band.floor_price >= Price(Decimal("17000"))

    def test_hose_tick_size_low_price(self) -> None:
        """HOSE: tick = 10 VND for price < 10,000."""
        band = calculate_price_band(Symbol("LOW"), Exchange.HOSE, Price(Decimal("8000")))
        assert band.tick_size == Decimal("10")

    def test_hose_tick_size_mid_price(self) -> None:
        """HOSE: tick = 50 VND for 10,000 ≤ price < 50,000."""
        band = calculate_price_band(Symbol("MID"), Exchange.HOSE, Price(Decimal("25000")))
        assert band.tick_size == Decimal("50")

    def test_hose_tick_size_high_price(self) -> None:
        """HOSE: tick = 100 VND for price ≥ 50,000."""
        band = calculate_price_band(Symbol("HIGH"), Exchange.HOSE, Price(Decimal("98500")))
        assert band.tick_size == Decimal("100")

    def test_ceiling_snaps_down(self) -> None:
        """Ceiling should snap DOWN to tick grid (conservative for buyers)."""
        band = calculate_price_band(Symbol("FPT"), Exchange.HOSE, Price(Decimal("98500")))
        # Ceiling = 98500 * 1.07 = 105395 → snap down to 105300
        assert band.ceiling_price % band.tick_size == 0

    def test_floor_snaps_up(self) -> None:
        """Floor should snap UP to tick grid (conservative for sellers)."""
        band = calculate_price_band(Symbol("FPT"), Exchange.HOSE, Price(Decimal("98500")))
        # Floor = 98500 * 0.93 = 91605 → snap up to 91700
        assert band.floor_price % band.tick_size == 0


class TestValidateOrderPrice:
    """Tests for validate_order_price()."""

    def _make_band(self) -> PriceBand:
        return calculate_price_band(Symbol("FPT"), Exchange.HOSE, Price(Decimal("100000")))

    def test_price_within_range(self) -> None:
        band = self._make_band()
        is_valid, reason = validate_order_price(Price(Decimal("100000")), band)
        assert is_valid is True
        assert "valid" in reason.lower()

    def test_price_above_ceiling(self) -> None:
        band = self._make_band()
        is_valid, reason = validate_order_price(Price(Decimal("110000")), band)
        assert is_valid is False
        assert "ceiling" in reason.lower()

    def test_price_below_floor(self) -> None:
        band = self._make_band()
        is_valid, reason = validate_order_price(Price(Decimal("80000")), band)
        assert is_valid is False
        assert "floor" in reason.lower()

    def test_price_not_aligned_to_tick(self) -> None:
        band = self._make_band()
        # 100050 is not aligned to tick=100
        is_valid, reason = validate_order_price(Price(Decimal("100050")), band)
        assert is_valid is False
        assert "tick size" in reason.lower()

    def test_price_at_ceiling_exact(self) -> None:
        band = self._make_band()
        is_valid, _ = validate_order_price(band.ceiling_price, band)
        assert is_valid is True

    def test_price_at_floor_exact(self) -> None:
        band = self._make_band()
        is_valid, _ = validate_order_price(band.floor_price, band)
        assert is_valid is True
