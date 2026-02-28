"""Property-based tests using hypothesis.

★ Tests financial invariants that must hold for ALL valid inputs.
★ Catches edge cases that unit tests miss.
★ Inspired by FinceptTerminal's comprehensive testing approach.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from core.entities.order import Order, OrderSide, OrderStatus, OrderType
from core.entities.portfolio import CashBalance, PortfolioState, Position
from core.entities.risk import RiskLimit
from core.use_cases.price_band import calculate_price_band
from core.use_cases.risk_check import validate_order
from core.value_objects import Price, Quantity, Symbol
from core.entities.tick import Exchange


# ── Strategies ────────────────────────────────────────────────

valid_price = st.decimals(
    min_value=Decimal("1000"), max_value=Decimal("1000000"),
    allow_nan=False, allow_infinity=False, places=0,
)

valid_quantity = st.integers(min_value=100, max_value=100000).filter(lambda q: q % 100 == 0)


def make_order(price: Decimal, quantity: int, side: OrderSide = OrderSide.BUY) -> Order:
    now = datetime(2026, 2, 10, 10, 0, 0)
    return Order(
        order_id="ORD-PROP", symbol=Symbol("FPT"), side=side, order_type=OrderType.LO,
        quantity=Quantity(quantity), price=Price(price),
        ceiling_price=Price(price * Decimal("1.07")), floor_price=Price(price * Decimal("0.93")),
        status=OrderStatus.CREATED, filled_quantity=Quantity(0), avg_fill_price=Price(Decimal("0")),
        broker_order_id=None, rejection_reason=None, idempotency_key="IDEM-PROP",
        created_at=now, updated_at=now,
    )


def make_portfolio(nav: Decimal, purchasing_power: Decimal) -> PortfolioState:
    return PortfolioState(
        positions=(Position(symbol=Symbol("FPT"), quantity=Quantity(1000), sellable_qty=Quantity(1000), receiving_t1=Quantity(0), receiving_t2=Quantity(0), avg_price=Price(Decimal("95000")), market_price=Price(nav / Decimal("1000"))),),
        cash=CashBalance(cash_bal=purchasing_power, purchasing_power=purchasing_power, pending_settlement=Decimal("0")),
        synced_at=datetime(2026, 2, 10, 9, 30, 0),
    )


# ── Price Band Properties ─────────────────────────────────────

@given(ref_price=valid_price)
@settings(max_examples=100)
def test_price_band_ceiling_always_above_floor(ref_price: Decimal) -> None:
    """INVARIANT: ceiling > reference > floor for any valid price."""
    band = calculate_price_band(Symbol("FPT"), Exchange.HOSE, Price(ref_price))
    assert band.ceiling > band.floor
    assert band.ceiling > ref_price
    assert band.floor < ref_price


@given(ref_price=valid_price)
@settings(max_examples=100)
def test_price_band_hose_7_percent(ref_price: Decimal) -> None:
    """INVARIANT: HOSE price band is approximately ±7%."""
    band = calculate_price_band(Symbol("FPT"), Exchange.HOSE, Price(ref_price))
    expected_ceiling = ref_price * Decimal("1.07")
    expected_floor = ref_price * Decimal("0.93")
    assert abs(band.ceiling - expected_ceiling) <= Decimal("100")
    assert abs(band.floor - expected_floor) <= Decimal("100")


# ── Risk Check Properties ─────────────────────────────────────

@given(price=valid_price, quantity=valid_quantity)
@settings(max_examples=50)
def test_kill_switch_always_rejects(price: Decimal, quantity: int) -> None:
    """INVARIANT: Kill switch active → ALWAYS rejected."""
    limits = RiskLimit(max_position_pct=Decimal("0.20"), max_daily_loss=Decimal("5000000"), kill_switch_active=True)
    order = make_order(price, quantity)
    portfolio = make_portfolio(nav=Decimal("1000000000"), purchasing_power=Decimal("500000000"))
    result = validate_order(order, portfolio, limits)
    assert result.approved is False
    assert "kill switch" in result.reason.lower()


@given(quantity=st.integers(min_value=1, max_value=99999).filter(lambda q: q % 100 != 0))
@settings(max_examples=50)
def test_non_lot_size_always_rejected(quantity: int) -> None:
    """INVARIANT: Quantity not multiple of 100 → ALWAYS rejected."""
    limits = RiskLimit(max_position_pct=Decimal("0.20"), max_daily_loss=Decimal("5000000"), kill_switch_active=False)
    order = make_order(Decimal("50000"), quantity)
    portfolio = make_portfolio(nav=Decimal("1000000000"), purchasing_power=Decimal("500000000"))
    result = validate_order(order, portfolio, limits)
    assert result.approved is False
    assert any("LOT_SIZE" in f for f in result.checks_failed)


# ── Portfolio Properties ──────────────────────────────────────

@given(
    market_price=valid_price,
    avg_price=valid_price,
    quantity=st.integers(min_value=100, max_value=100000),
)
@settings(max_examples=100)
def test_unrealized_pnl_sign_matches_price_direction(market_price: Decimal, avg_price: Decimal, quantity: int) -> None:
    """INVARIANT: PnL sign matches price direction."""
    position = Position(
        symbol=Symbol("FPT"), quantity=Quantity(quantity), sellable_qty=Quantity(quantity),
        receiving_t1=Quantity(0), receiving_t2=Quantity(0),
        avg_price=Price(avg_price), market_price=Price(market_price),
    )
    if market_price > avg_price:
        assert position.unrealized_pnl > 0
    elif market_price < avg_price:
        assert position.unrealized_pnl < 0
    else:
        assert position.unrealized_pnl == 0


@given(
    cash_bal=st.decimals(min_value=Decimal("0"), max_value=Decimal("1000000000"), places=0),
    purchasing_power=st.decimals(min_value=Decimal("0"), max_value=Decimal("2000000000"), places=0),
)
@settings(max_examples=50)
def test_total_available_is_cash_bal(cash_bal: Decimal, purchasing_power: Decimal) -> None:
    """INVARIANT: total_available == cash_bal (conservative)."""
    cash = CashBalance(cash_bal=cash_bal, purchasing_power=purchasing_power, pending_settlement=Decimal("0"))
    assert cash.total_available == cash_bal
