"""BrokerPort — outbound port for order execution.

Ref: Doc 02 §2.3, Doc 05 §2
"""

from __future__ import annotations

from typing import Protocol

from core.entities.order import Order
from core.value_objects import Symbol


class BrokerPort(Protocol):
    """Outbound port: place, cancel, and query orders with any broker."""

    async def place_order(self, order: Order) -> Order:
        """Submit order to broker. Returns updated Order with broker_order_id."""
        ...

    async def cancel_order(self, order_id: str) -> Order:
        """Cancel an existing order. Returns updated Order."""
        ...

    async def get_order_status(self, order_id: str) -> Order:
        """Query current order status from broker."""
        ...

    async def get_open_orders(self, symbol: Symbol | None = None) -> list[Order]:
        """Get all open orders, optionally filtered by symbol."""
        ...
