"""Repository ports — persist and query domain data.

★ Protocol-based structural subtyping.
★ DuckDB adapter implements these in packages/adapters/duckdb/.

Ref: Doc 02 §2.3
"""

from __future__ import annotations

from datetime import date
from typing import Protocol

from core.entities.order import Order
from core.entities.tick import Tick
from core.value_objects import Symbol


class TickRepository(Protocol):
    """Outbound port: persist and query tick data."""

    async def insert_batch(self, ticks: list[Tick]) -> int:
        """Insert a batch of ticks. Returns number of rows inserted."""
        ...

    async def get_ohlcv(
        self,
        symbol: Symbol,
        start: date,
        end: date,
    ) -> list[dict[str, object]]:
        """Get OHLCV candle data for a symbol in a date range."""
        ...

    async def asof_join_orders(
        self,
        orders: list[Order],
    ) -> list[dict[str, object]]:
        """ASOF JOIN: find nearest tick price at each order's timestamp."""
        ...


class OrderRepository(Protocol):
    """Outbound port: persist and query orders."""

    async def save(self, order: Order) -> None:
        """Save or update an order."""
        ...

    async def get_by_id(self, order_id: str) -> Order | None:
        """Get order by ID. Returns None if not found."""
        ...

    async def get_by_symbol(self, symbol: Symbol) -> list[Order]:
        """Get all orders for a symbol."""
        ...

    async def get_open_orders(self) -> list[Order]:
        """Get all non-terminal orders."""
        ...
