"""Unit tests for core domain entities.

Tests:
- Immutability (frozen dataclasses)
- Equality
- is_ceiling() / is_floor() on Tick
- Order FSM: valid + invalid transitions
- Portfolio: NAV, PnL, sellable qty

Ref: Doc 02 §5.3
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest
from core.entities.order import (
    InvalidOrderTransitionError,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
)
from core.entities.portfolio import CashBalance, PortfolioState, Position
from core.entities.risk import RiskLimit
from core.entities.signal import AgentSource, SignalStrength, TradingSignal
from core.entities.tick import Exchange, Tick
from core.value_objects import Price, Quantity, Symbol

# ═══════════════════════════════════════════════════════════════
# Tick Entity Tests
# ═══════════════════════════════════════════════════════════════


class TestTick:
    """Tests for Tick entity."""

    def test_tick_is_immutable(self) -> None:
        tick = Tick(
            symbol=Symbol("FPT"),
            price=Price(Decimal("98500")),
            volume=Quantity(1000),
            exchange=Exchange.HOSE,
            timestamp=datetime(2026, 2, 10, 9, 0, 0),
        )
        with pytest.raises(AttributeError):
            tick.price = Price(Decimal("99000"))  # type: ignore[misc]

    def test_tick_equality(self) -> None:
        tick_a = Tick(
            symbol=Symbol("FPT"),
            price=Price(Decimal("98500")),
            volume=Quantity(1000),
            exchange=Exchange.HOSE,
            timestamp=datetime(2026, 2, 10, 9, 0, 0),
        )
        tick_b = Tick(
            symbol=Symbol("FPT"),
            price=Price(Decimal("98500")),
            volume=Quantity(1000),
            exchange=Exchange.HOSE,
            timestamp=datetime(2026, 2, 10, 9, 0, 0),
        )
        assert tick_a == tick_b

    def test_tick_is_hashable(self) -> None:
        tick = Tick(
            symbol=Symbol("FPT"),
            price=Price(Decimal("98500")),
            volume=Quantity(1000),
            exchange=Exchange.HOSE,
            timestamp=datetime(2026, 2, 10, 9, 0, 0),
        )
        assert isinstance(hash(tick), int)
        # Can be added to sets
        assert len({tick, tick}) == 1

    def test_exchange_enum_values(self) -> None:
        assert Exchange.HOSE == "HOSE"
        assert Exchange.HNX == "HNX"
        assert Exchange.UPCOM == "UPCOM"


# ═══════════════════════════════════════════════════════════════
# Order Entity Tests
# ═══════════════════════════════════════════════════════════════


class TestOrder:
    """Tests for Order entity and FSM transitions."""

    def _make_order(self, status: OrderStatus = OrderStatus.CREATED) -> Order:
        now = datetime(2026, 2, 10, 10, 0, 0)
        return Order(
            order_id="ORD-001",
            symbol=Symbol("FPT"),
            side=OrderSide.BUY,
            order_type=OrderType.LO,
            quantity=Quantity(1000),
            price=Price(Decimal("98500")),
            ceiling_price=Price(Decimal("105400")),
            floor_price=Price(Decimal("91600")),
            status=status,
            filled_quantity=Quantity(0),
            avg_fill_price=Price(Decimal("0")),
            broker_order_id=None,
            rejection_reason=None,
            idempotency_key="IDEM-001",
            created_at=now,
            updated_at=now,
        )

    def test_order_is_immutable(self) -> None:
        order = self._make_order()
        with pytest.raises(AttributeError):
            order.status = OrderStatus.PENDING  # type: ignore[misc]

    def test_valid_transition_created_to_pending(self) -> None:
        order = self._make_order(OrderStatus.CREATED)
        new_order = order.transition_to(OrderStatus.PENDING)
        assert new_order.status == OrderStatus.PENDING
        assert order.status == OrderStatus.CREATED  # Original unchanged

    def test_valid_transition_created_to_rejected(self) -> None:
        order = self._make_order(OrderStatus.CREATED)
        new_order = order.transition_to(OrderStatus.REJECTED)
        assert new_order.status == OrderStatus.REJECTED

    def test_valid_transition_pending_to_matched(self) -> None:
        order = self._make_order(OrderStatus.PENDING)
        new_order = order.transition_to(OrderStatus.MATCHED)
        assert new_order.status == OrderStatus.MATCHED

    def test_valid_transition_pending_to_partial_fill(self) -> None:
        order = self._make_order(OrderStatus.PENDING)
        new_order = order.transition_to(OrderStatus.PARTIAL_FILL)
        assert new_order.status == OrderStatus.PARTIAL_FILL

    def test_valid_transition_partial_fill_to_matched(self) -> None:
        order = self._make_order(OrderStatus.PARTIAL_FILL)
        new_order = order.transition_to(OrderStatus.MATCHED)
        assert new_order.status == OrderStatus.MATCHED

    def test_invalid_transition_created_to_matched(self) -> None:
        order = self._make_order(OrderStatus.CREATED)
        with pytest.raises(InvalidOrderTransitionError):
            order.transition_to(OrderStatus.MATCHED)

    def test_invalid_transition_matched_to_anything(self) -> None:
        """Terminal state: MATCHED cannot transition to anything."""
        order = self._make_order(OrderStatus.MATCHED)
        for target_status in OrderStatus:
            if target_status == OrderStatus.MATCHED:
                continue
            with pytest.raises(InvalidOrderTransitionError):
                order.transition_to(target_status)

    def test_invalid_transition_rejected_to_anything(self) -> None:
        """Terminal state: REJECTED cannot transition."""
        order = self._make_order(OrderStatus.REJECTED)
        with pytest.raises(InvalidOrderTransitionError):
            order.transition_to(OrderStatus.PENDING)

    def test_invalid_transition_cancelled_to_anything(self) -> None:
        """Terminal state: CANCELLED cannot transition."""
        order = self._make_order(OrderStatus.CANCELLED)
        with pytest.raises(InvalidOrderTransitionError):
            order.transition_to(OrderStatus.PENDING)

    def test_is_terminal_property(self) -> None:
        assert self._make_order(OrderStatus.MATCHED).is_terminal is True
        assert self._make_order(OrderStatus.REJECTED).is_terminal is True
        assert self._make_order(OrderStatus.CANCELLED).is_terminal is True
        assert self._make_order(OrderStatus.CREATED).is_terminal is False
        assert self._make_order(OrderStatus.PENDING).is_terminal is False

    def test_remaining_quantity(self) -> None:
        order = self._make_order()
        assert order.remaining_quantity == 1000  # 1000 - 0

    def test_order_value(self) -> None:
        order = self._make_order()
        expected = Decimal("98500") * Decimal("1000")
        assert order.order_value == expected

    def test_order_side_enum(self) -> None:
        assert OrderSide.BUY == "BUY"
        assert OrderSide.SELL == "SELL"

    def test_order_type_enum(self) -> None:
        assert OrderType.LO == "LO"
        assert OrderType.ATO == "ATO"
        assert OrderType.ATC == "ATC"
        assert OrderType.MP == "MP"


# ═══════════════════════════════════════════════════════════════
# Portfolio Entity Tests
# ═══════════════════════════════════════════════════════════════


class TestPortfolio:
    """Tests for Position, CashBalance, PortfolioState."""

    def test_position_unrealized_pnl(self) -> None:
        position = Position(
            symbol=Symbol("FPT"),
            quantity=Quantity(1000),
            sellable_qty=Quantity(500),
            receiving_t1=Quantity(250),
            receiving_t2=Quantity(250),
            avg_price=Price(Decimal("95000")),
            market_price=Price(Decimal("98000")),
        )
        # PnL = (98000 - 95000) * 1000 = 3,000,000
        assert position.unrealized_pnl == Decimal("3000000")

    def test_position_market_value(self) -> None:
        position = Position(
            symbol=Symbol("FPT"),
            quantity=Quantity(1000),
            sellable_qty=Quantity(500),
            receiving_t1=Quantity(250),
            receiving_t2=Quantity(250),
            avg_price=Price(Decimal("95000")),
            market_price=Price(Decimal("98000")),
        )
        assert position.market_value == Decimal("98000000")

    def test_portfolio_nav(self, sample_portfolio: PortfolioState) -> None:
        # NAV = position_value + cash_bal
        # position_value = 98500 * 2000 = 197,000,000
        # cash_bal = 50,000,000
        # NAV = 247,000,000
        expected = Decimal("98500") * Decimal("2000") + Decimal("50000000")
        assert sample_portfolio.net_asset_value == expected

    def test_portfolio_get_position_found(self, sample_portfolio: PortfolioState) -> None:
        position = sample_portfolio.get_position(Symbol("FPT"))
        assert position is not None
        assert position.symbol == "FPT"

    def test_portfolio_get_position_not_found(self, sample_portfolio: PortfolioState) -> None:
        position = sample_portfolio.get_position(Symbol("VIC"))
        assert position is None

    def test_portfolio_get_sellable_qty(self, sample_portfolio: PortfolioState) -> None:
        assert sample_portfolio.get_sellable_qty(Symbol("FPT")) == 1000
        assert sample_portfolio.get_sellable_qty(Symbol("VIC")) == 0

    def test_cash_balance_total_available(self) -> None:
        cash = CashBalance(
            cash_bal=Decimal("50000000"),
            purchasing_power=Decimal("80000000"),
            pending_settlement=Decimal("10000000"),
        )
        assert cash.total_available == Decimal("50000000")


# ═══════════════════════════════════════════════════════════════
# Risk Entity Tests
# ═══════════════════════════════════════════════════════════════


class TestRiskLimit:
    """Tests for RiskLimit entity."""

    def test_risk_limit_is_immutable(self, default_risk_limits: RiskLimit) -> None:
        with pytest.raises(AttributeError):
            default_risk_limits.kill_switch_active = True  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════
# Signal Entity Tests
# ═══════════════════════════════════════════════════════════════


class TestTradingSignal:
    """Tests for TradingSignal entity."""

    def test_signal_is_immutable(self) -> None:
        signal = TradingSignal(
            signal_id="SIG-001",
            symbol=Symbol("FPT"),
            strength=SignalStrength.BUY,
            source=AgentSource.TECHNICAL,
            target_price=Price(Decimal("100000")),
            stop_loss=Price(Decimal("90000")),
            confidence=Decimal("0.85"),
            reasoning="RSI oversold + MACD bullish cross",
            created_at=datetime(2026, 2, 10, 10, 0, 0),
        )
        with pytest.raises(AttributeError):
            signal.strength = SignalStrength.SELL  # type: ignore[misc]

    def test_signal_strength_enum(self) -> None:
        assert SignalStrength.STRONG_BUY == "STRONG_BUY"
        assert SignalStrength.NEUTRAL == "NEUTRAL"
        assert SignalStrength.STRONG_SELL == "STRONG_SELL"
