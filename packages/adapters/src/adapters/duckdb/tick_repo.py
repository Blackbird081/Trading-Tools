"""DuckDB TickRepository — implements core.ports.repository.TickRepository.

★ Protocol structural subtyping: no inheritance required.
★ mypy verifies compatibility at type-check time.
★ All DuckDB calls are synchronous (C FFI) — caller must use asyncio.to_thread().

Ref: Doc 02 §2.5
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import duckdb

if TYPE_CHECKING:
    from core.entities.order import Order
    from core.entities.tick import Tick


class DuckDBTickRepository:
    """Implements core.ports.repository.TickRepository via DuckDB."""

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    async def insert_batch(self, ticks: list[Tick]) -> int:
        """Insert a batch of ticks into DuckDB.

        ★ CRITICAL: This is an async interface but DuckDB is blocking.
        ★ In production, caller MUST wrap with asyncio.to_thread().
        """
        if not ticks:
            return 0

        rows = [(t.symbol, float(t.price), t.volume, t.exchange.value, t.timestamp) for t in ticks]
        self._conn.executemany(
            """
            INSERT INTO ticks (symbol, price, volume, exchange, ts)
            VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )
        return len(rows)

    async def get_ohlcv(
        self,
        symbol: str,
        start: date,
        end: date,
    ) -> list[dict[str, object]]:
        """Get OHLCV candle data for a symbol in a date range."""
        result = self._conn.execute(
            """
            SELECT
                symbol,
                FIRST(price ORDER BY ts) AS open,
                MAX(price)               AS high,
                MIN(price)               AS low,
                LAST(price ORDER BY ts)  AS close,
                SUM(volume)              AS volume,
                DATE_TRUNC('day', ts)    AS trading_date
            FROM ticks
            WHERE symbol = ?
              AND CAST(ts AS DATE) BETWEEN ? AND ?
            GROUP BY symbol, DATE_TRUNC('day', ts)
            ORDER BY trading_date
            """,
            [symbol, start.isoformat(), end.isoformat()],
        )
        columns = [desc[0] for desc in result.description]
        return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]

    async def asof_join_orders(
        self,
        orders: list[Order],
    ) -> list[dict[str, object]]:
        """ASOF JOIN: find nearest tick price at each order's timestamp.

        ★ O(N + M) merge-sort complexity — vastly faster than LATERAL JOIN.
        ★ See Doc 02 §3.1 for detailed explanation.
        """
        result = self._conn.execute(
            """
            SELECT
                o.order_id,
                o.symbol,
                o.side,
                o.quantity,
                o.req_price,
                o.created_at   AS order_time,
                t.price        AS market_price_at_order,
                t.ts           AS tick_time,
                ABS(o.req_price - t.price) AS slippage,
                CASE
                    WHEN o.side = 'SELL'
                    THEN (o.req_price - t.price) * o.quantity
                    ELSE NULL
                END AS estimated_pnl
            FROM orders o
            ASOF JOIN ticks t
                ON  o.symbol = t.symbol
                AND o.created_at >= t.ts
            ORDER BY o.created_at DESC
            """
        )
        columns = [desc[0] for desc in result.description]
        return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]

    def insert_batch_sync(self, ticks: list[Tick]) -> int:
        """Synchronous version for direct calls (tests, thread pool)."""
        if not ticks:
            return 0

        rows = [(t.symbol, float(t.price), t.volume, t.exchange.value, t.timestamp) for t in ticks]
        self._conn.executemany(
            """
            INSERT INTO ticks (symbol, price, volume, exchange, ts)
            VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )
        return len(rows)
