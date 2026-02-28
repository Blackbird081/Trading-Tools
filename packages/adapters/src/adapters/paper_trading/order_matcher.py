"""Paper Trading Order Matcher — simulates order execution.

★ Inspired by FinceptTerminal's PaperOrderMatcher.
★ Scoped by portfolio_id:symbol to prevent cross-broker contamination.
"""
from __future__ import annotations
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from core.entities.order import Order, OrderSide, OrderStatus
from core.value_objects import Symbol

logger = logging.getLogger("paper_trading.matcher")


@dataclass
class PriceData:
    symbol: str
    last: Decimal
    bid: Decimal | None = None
    ask: Decimal | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class OrderFillEvent:
    order_id: str
    symbol: str
    side: OrderSide
    order_type: str
    fill_price: Decimal
    quantity: int
    timestamp: datetime


OrderFillCallback = Callable[[OrderFillEvent], None]


class PaperOrderMatcher:
    """Paper trading order matching engine."""

    def __init__(self) -> None:
        self._pending: dict[str, list[Order]] = {}
        self._fill_callbacks: set[OrderFillCallback] = set()
        self._positions: dict[str, dict[str, int]] = {}
        self._cash: dict[str, Decimal] = {}

    def _scoped_key(self, portfolio_id: str, symbol: str) -> str:
        return f"{portfolio_id}:{symbol}"

    def initialize_portfolio(self, portfolio_id: str, initial_cash: Decimal) -> None:
        self._cash[portfolio_id] = initial_cash
        self._positions[portfolio_id] = {}

    def add_order(self, order: Order, portfolio_id: str) -> bool:
        if order.status != OrderStatus.CREATED:
            return False
        if order.side == OrderSide.BUY:
            order_value = Decimal(str(order.price)) * order.quantity
            if order_value > self._cash.get(portfolio_id, Decimal("0")):
                return False
        key = self._scoped_key(portfolio_id, str(order.symbol))
        self._pending.setdefault(key, []).append(order)
        return True

    def remove_order(self, order_id: str) -> bool:
        for key, orders in list(self._pending.items()):
            idx = next((i for i, o in enumerate(orders) if o.order_id == order_id), -1)
            if idx >= 0:
                orders.pop(idx)
                if not orders:
                    del self._pending[key]
                return True
        return False

    async def check_orders(self, symbol: str, price: PriceData, portfolio_id: str) -> list[OrderFillEvent]:
        key = self._scoped_key(portfolio_id, symbol)
        orders = self._pending.get(key, [])
        if not orders:
            return []
        fills: list[OrderFillEvent] = []
        to_remove: list[str] = []
        for order in orders:
            should_fill, fill_price = self._should_fill(order, price)
            if should_fill and fill_price is not None:
                event = await self._fill_order(order, fill_price, portfolio_id)
                if event:
                    fills.append(event)
                    to_remove.append(order.order_id)
        for oid in to_remove:
            self.remove_order(oid)
        return fills

    def _should_fill(self, order: Order, price: PriceData) -> tuple[bool, Decimal | None]:
        ot = order.order_type.value
        if ot == "LO":
            limit_price = Decimal(str(order.price))
            if order.side == OrderSide.BUY:
                ask = price.ask or price.last
                if ask <= limit_price:
                    return True, limit_price
            else:
                bid = price.bid or price.last
                if bid >= limit_price:
                    return True, limit_price
        elif ot in ("MP", "ATO", "ATC"):
            return True, price.last
        return False, None

    async def _fill_order(self, order: Order, fill_price: Decimal, portfolio_id: str) -> OrderFillEvent | None:
        try:
            positions = self._positions.setdefault(portfolio_id, {})
            symbol = str(order.symbol)
            if order.side == OrderSide.BUY:
                self._cash[portfolio_id] = self._cash.get(portfolio_id, Decimal("0")) - fill_price * order.quantity
                positions[symbol] = positions.get(symbol, 0) + order.quantity
            else:
                self._cash[portfolio_id] = self._cash.get(portfolio_id, Decimal("0")) + fill_price * order.quantity
                positions[symbol] = max(0, positions.get(symbol, 0) - order.quantity)
            event = OrderFillEvent(order_id=order.order_id, symbol=symbol, side=order.side, order_type=order.order_type.value, fill_price=fill_price, quantity=order.quantity, timestamp=datetime.now(UTC))
            for cb in self._fill_callbacks:
                try:
                    cb(event)
                except Exception:
                    pass
            return event
        except Exception:
            logger.exception("Failed to fill paper order %s", order.order_id)
            return None

    def on_order_fill(self, callback: OrderFillCallback) -> Callable[[], None]:
        self._fill_callbacks.add(callback)
        return lambda: self._fill_callbacks.discard(callback)

    def get_portfolio_state(self, portfolio_id: str) -> dict[str, object]:
        return {"portfolio_id": portfolio_id, "cash": str(self._cash.get(portfolio_id, Decimal("0"))), "positions": dict(self._positions.get(portfolio_id, {}))}

    def clear_portfolio(self, portfolio_id: str) -> None:
        for key in [k for k in self._pending if k.startswith(f"{portfolio_id}:")]:
            del self._pending[key]


_matcher_instance: PaperOrderMatcher | None = None


def get_paper_order_matcher() -> PaperOrderMatcher:
    global _matcher_instance  # noqa: PLW0603
    if _matcher_instance is None:
        _matcher_instance = PaperOrderMatcher()
    return _matcher_instance
