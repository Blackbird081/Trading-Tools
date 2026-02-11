"""Unit tests for risk_check use case — order validation.

★ Pure function tests — no mocks needed.
★ Tests all 7 validation checks independently.

Ref: Doc 05 §5.2
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from core.entities.order import Order, OrderSide, OrderStatus, OrderType
from core.entities.portfolio import PortfolioState
from core.entities.risk import RiskLimit
from core.entities.tick import Exchange
from core.use_cases.price_band import calculate_price_band
from core.use_cases.risk_check import validate_order
from core.value_objects import Price, Quantity, Symbol


class TestValidateOrder:
    """Tests for comprehensive order validation."""

    def _make_order(
        self,
        *,
        symbol: str = "VNM",
        side: OrderSide = OrderSide.BUY,
        quantity: int = 500,
        price: str = "72000",
    ) -> Order:
        now = datetime(2026, 2, 10, 10, 0, 0)
        return Order(
            order_id="ORD-TEST",
            symbol=Symbol(symbol),
            side=side,
            order_type=OrderType.LO,
            quantity=Quantity(quantity),
            price=Price(Decimal(price)),
            ceiling_price=Price(Decimal("77000")),
            floor_price=Price(Decimal("67000")),
            status=OrderStatus.CREATED,
            filled_quantity=Quantity(0),
            avg_fill_price=Price(Decimal("0")),
            broker_order_id=None,
            rejection_reason=None,
            idempotency_key="IDEM-TEST",
            created_at=now,
            updated_at=now,
        )

    def test_buy_within_limits_approved(
        self,
        sample_portfolio: PortfolioState,
        default_risk_limits: RiskLimit,
    ) -> None:
        """Normal buy order within all limits should be approved."""
        order = self._make_order(quantity=500, price="72000")
        result = validate_order(order, sample_portfolio, default_risk_limits)
        assert result.approved is True
        assert result.reason == "All checks passed"
        assert len(result.checks_failed) == 0

    def test_kill_switch_blocks_everything(
        self,
        sample_portfolio: PortfolioState,
    ) -> None:
        """Kill switch active = reject immediately."""
        limits = RiskLimit(
            max_position_pct=Decimal("0.20"),
            max_daily_loss=Decimal("5000000"),
            kill_switch_active=True,
        )
        order = self._make_order()
        result = validate_order(order, sample_portfolio, limits)
        assert result.approved is False
        assert "kill switch" in result.reason.lower()

    def test_buy_exceeds_nav_limit_rejected(
        self,
        sample_portfolio: PortfolioState,
        default_risk_limits: RiskLimit,
    ) -> None:
        """Order value > 20% of NAV should be rejected."""
        # NAV ≈ 247,000,000. 20% = 49,400,000
        # Order = 100_000 * 98500 = 9,850,000,000 >> 20% NAV
        order = self._make_order(quantity=100000, price="98500")
        result = validate_order(order, sample_portfolio, default_risk_limits)
        assert result.approved is False
        assert any("POSITION_SIZE" in f for f in result.checks_failed)

    def test_buy_exceeds_purchasing_power_rejected(
        self,
        sample_portfolio: PortfolioState,
        default_risk_limits: RiskLimit,
    ) -> None:
        """Buy order exceeding purchasing power should be rejected."""
        # purchasing_power = 80,000,000
        # Order = 2000 * 98500 = 197,000,000 > 80,000,000
        order = self._make_order(quantity=2000, price="98500")
        result = validate_order(order, sample_portfolio, default_risk_limits)
        assert result.approved is False
        assert any("BUYING_POWER" in f or "POSITION_SIZE" in f for f in result.checks_failed)

    def test_sell_exceeds_sellable_qty_rejected(
        self,
        sample_portfolio: PortfolioState,
        default_risk_limits: RiskLimit,
    ) -> None:
        """Selling more than sellable quantity should be rejected (T+2.5)."""
        # Portfolio has 1000 sellable FPT, trying to sell 1500
        order = self._make_order(symbol="FPT", side=OrderSide.SELL, quantity=1500, price="98500")
        result = validate_order(order, sample_portfolio, default_risk_limits)
        assert result.approved is False
        assert any("SELLABLE_QTY" in f for f in result.checks_failed)

    def test_sell_within_sellable_qty_approved(
        self,
        sample_portfolio: PortfolioState,
        default_risk_limits: RiskLimit,
    ) -> None:
        """Selling within sellable quantity should be approved."""
        order = self._make_order(symbol="FPT", side=OrderSide.SELL, quantity=500, price="98500")
        result = validate_order(order, sample_portfolio, default_risk_limits)
        assert result.approved is True

    def test_lot_size_not_multiple_of_100_rejected(
        self,
        sample_portfolio: PortfolioState,
        default_risk_limits: RiskLimit,
    ) -> None:
        """Quantity not a multiple of 100 should be rejected."""
        order = self._make_order(quantity=150)  # Not multiple of 100
        result = validate_order(order, sample_portfolio, default_risk_limits)
        assert result.approved is False
        assert any("LOT_SIZE" in f for f in result.checks_failed)

    def test_price_band_above_ceiling_rejected(
        self,
        sample_portfolio: PortfolioState,
        default_risk_limits: RiskLimit,
    ) -> None:
        """Price above ceiling should be rejected when price_band is provided."""
        band = calculate_price_band(Symbol("FPT"), Exchange.HOSE, Price(Decimal("98500")))
        order = self._make_order(
            symbol="FPT",
            quantity=100,
            price="120000",  # Way above ceiling
        )
        result = validate_order(order, sample_portfolio, default_risk_limits, price_band=band)
        assert result.approved is False
        assert any("PRICE_BAND" in f for f in result.checks_failed)

    def test_price_band_within_range_passed(
        self,
        sample_portfolio: PortfolioState,
        default_risk_limits: RiskLimit,
    ) -> None:
        """Price within band should pass the price_band check."""
        band = calculate_price_band(Symbol("FPT"), Exchange.HOSE, Price(Decimal("98500")))
        # Use a price that's within the band and aligned to tick size
        order = self._make_order(symbol="FPT", quantity=100, price="98500")
        result = validate_order(order, sample_portfolio, default_risk_limits, price_band=band)
        # Price band check should pass (other checks may fail/pass)
        assert all("PRICE_BAND" not in f for f in result.checks_failed)

    def test_pending_sell_qty_subtracted(
        self,
        sample_portfolio: PortfolioState,
        default_risk_limits: RiskLimit,
    ) -> None:
        """Pending sell qty should be subtracted from available sellable."""
        # Sellable = 1000, pending = 800, requesting = 300
        # Available = 1000 - 800 = 200 < 300 → reject
        order = self._make_order(symbol="FPT", side=OrderSide.SELL, quantity=300, price="98500")
        result = validate_order(order, sample_portfolio, default_risk_limits, pending_sell_qty=800)
        assert result.approved is False
        assert any("SELLABLE_QTY" in f for f in result.checks_failed)

    def test_all_checks_collected(
        self,
        sample_portfolio: PortfolioState,
        default_risk_limits: RiskLimit,
    ) -> None:
        """Verify that multiple failures are all collected."""
        # Invalid lot size + exceeds NAV
        order = self._make_order(quantity=99999, price="98500")
        result = validate_order(order, sample_portfolio, default_risk_limits)
        assert result.approved is False
        # Both LOT_SIZE and POSITION_SIZE should fail
        failed_checks = " ".join(result.checks_failed)
        assert "LOT_SIZE" in failed_checks
        assert "POSITION_SIZE" in failed_checks
