"""DuckDB OrderRepository — implements core.ports.repository.OrderRepository.

★ Protocol structural subtyping: no inheritance required.
★ Idempotency key prevents duplicate orders.

Ref: Doc 02 §2.5, Doc 05 §2.3
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import duckdb
from core.entities.order import (
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
)
from core.value_objects import Price, Quantity, Symbol


class DuckDBOrderRepository:
    """Implements core.ports.repository.OrderRepository via DuckDB."""

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    async def save(self, order: Order) -> None:
        """Save or upsert an order (by order_id)."""
        # Check if order exists
        existing = self._conn.execute(
            "SELECT order_id FROM orders WHERE order_id = ?",
            [order.order_id],
        ).fetchone()

        if existing:
            # Update existing order
            self._conn.execute(
                """
                UPDATE orders SET
                    status = ?,
                    filled_quantity = ?,
                    avg_fill_price = ?,
                    broker_order_id = ?,
                    rejection_reason = ?,
                    updated_at = ?
                WHERE order_id = ?
                """,
                [
                    order.status.value,
                    order.filled_quantity,
                    float(order.avg_fill_price),
                    order.broker_order_id,
                    order.rejection_reason,
                    order.updated_at.isoformat(),
                    order.order_id,
                ],
            )
        else:
            # Insert new order
            self._conn.execute(
                """
                INSERT INTO orders (
                    order_id, symbol, side, order_type, quantity, req_price,
                    ceiling_price, floor_price, status, filled_quantity,
                    avg_fill_price, broker_order_id, rejection_reason,
                    idempotency_key, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    order.order_id,
                    order.symbol,
                    order.side.value,
                    order.order_type.value,
                    order.quantity,
                    float(order.price),
                    float(order.ceiling_price),
                    float(order.floor_price),
                    order.status.value,
                    order.filled_quantity,
                    float(order.avg_fill_price),
                    order.broker_order_id,
                    order.rejection_reason,
                    order.idempotency_key,
                    order.created_at.isoformat(),
                    order.updated_at.isoformat(),
                ],
            )

    async def get_by_id(self, order_id: str) -> Order | None:
        """Get order by ID."""
        row = self._conn.execute(
            "SELECT * FROM orders WHERE order_id = ?",
            [order_id],
        ).fetchone()

        if row is None:
            return None

        return self._row_to_order(row)

    async def get_by_symbol(self, symbol: Symbol) -> list[Order]:
        """Get all orders for a symbol."""
        rows = self._conn.execute(
            "SELECT * FROM orders WHERE symbol = ? ORDER BY created_at DESC",
            [symbol],
        ).fetchall()
        return [self._row_to_order(row) for row in rows]

    async def get_open_orders(self) -> list[Order]:
        """Get all non-terminal orders."""
        rows = self._conn.execute(
            """
            SELECT * FROM orders
            WHERE status NOT IN ('MATCHED', 'REJECTED', 'BROKER_REJECTED', 'CANCELLED')
            ORDER BY created_at DESC
            """,
        ).fetchall()
        return [self._row_to_order(row) for row in rows]

    def _row_to_order(self, row: tuple[object, ...]) -> Order:
        """Convert a database row tuple to an Order entity."""
        return Order(
            order_id=str(row[0]),
            symbol=Symbol(str(row[1])),
            side=OrderSide(str(row[2])),
            order_type=OrderType(str(row[3])),
            quantity=Quantity(int(row[4]) if isinstance(row[4], (int, float)) else 0),
            price=Price(Decimal(str(row[5]))),
            ceiling_price=Price(Decimal(str(row[6]))),
            floor_price=Price(Decimal(str(row[7]))),
            status=OrderStatus(str(row[8])),
            filled_quantity=Quantity(int(row[9]) if isinstance(row[9], (int, float)) else 0),
            avg_fill_price=Price(Decimal(str(row[10]))),
            broker_order_id=str(row[11]) if row[11] is not None else None,
            rejection_reason=str(row[12]) if row[12] is not None else None,
            idempotency_key=str(row[13]),
            created_at=datetime.fromisoformat(str(row[14])),
            updated_at=datetime.fromisoformat(str(row[15])),
        )
