"""Integration tests for DuckDB repositories.

★ Uses real DuckDB (in-memory) — no mocks.
★ Tests tick insertion, ASOF JOIN, order CRUD, Parquet round-trip.

Ref: Doc 02 §5.4
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest
from adapters.duckdb.connection import create_connection
from adapters.duckdb.order_repo import DuckDBOrderRepository
from adapters.duckdb.tick_repo import DuckDBTickRepository
from core.entities.order import Order, OrderSide, OrderStatus, OrderType
from core.entities.tick import Tick
from core.value_objects import Price, Quantity, Symbol


class TestDuckDBTickRepository:
    """Integration tests for DuckDBTickRepository."""

    def test_insert_batch_and_count(
        self, duckdb_conn: duckdb.DuckDBPyConnection, sample_ticks: list[Tick]
    ) -> None:
        repo = DuckDBTickRepository(duckdb_conn)
        count = repo.insert_batch_sync(sample_ticks)
        assert count == len(sample_ticks)

        result = duckdb_conn.execute("SELECT COUNT(*) FROM ticks").fetchone()
        assert result is not None
        assert result[0] == len(sample_ticks)

    def test_insert_empty_batch(self, duckdb_conn: duckdb.DuckDBPyConnection) -> None:
        repo = DuckDBTickRepository(duckdb_conn)
        count = repo.insert_batch_sync([])
        assert count == 0

    def test_asof_join_matches_nearest_tick(self, duckdb_conn: duckdb.DuckDBPyConnection) -> None:
        """Verify ASOF JOIN returns the tick closest to (but not after) order time."""
        # Insert ticks at t=1s, t=3s, t=5s
        duckdb_conn.execute("""
            INSERT INTO ticks VALUES
                ('FPT', 98000, 1000, 'HOSE', '2026-02-10 09:00:01'),
                ('FPT', 98500, 2000, 'HOSE', '2026-02-10 09:00:03'),
                ('FPT', 99000, 1500, 'HOSE', '2026-02-10 09:00:05');
        """)
        # Insert order at t=4s (between tick t=3s and t=5s)
        duckdb_conn.execute("""
            INSERT INTO orders VALUES
                ('ORD-1', 'FPT', 'BUY', 'LO', 500, 98700, 105400, 91600,
                 'FILLED', 500, 98500, 'BRK-1', NULL, 'IDEM-1',
                 '2026-02-10 09:00:04', '2026-02-10 09:00:04');
        """)

        result = duckdb_conn.execute("""
            SELECT o.order_id, t.price, t.ts
            FROM orders o
            ASOF JOIN ticks t
                ON o.symbol = t.symbol
                AND o.created_at >= t.ts
        """).fetchone()

        assert result is not None
        assert result[0] == "ORD-1"
        assert result[1] == 98500  # Matched tick at t=3s, NOT t=5s
        assert "09:00:03" in str(result[2])

    def test_parquet_round_trip(
        self, duckdb_conn: duckdb.DuckDBPyConnection, tmp_path: Path
    ) -> None:
        """Write to Parquet, read back, verify data integrity."""
        duckdb_conn.execute("""
            INSERT INTO ticks VALUES
                ('VNM', 72000, 5000, 'HOSE', '2026-02-10 10:00:00');
        """)
        parquet_path = str(tmp_path / "test.parquet").replace("\\", "/")
        duckdb_conn.execute(f"""
            COPY ticks TO '{parquet_path}' (FORMAT PARQUET)
        """)
        result = duckdb_conn.execute(f"""
            SELECT symbol, price FROM read_parquet('{parquet_path}')
        """).fetchone()

        assert result is not None
        assert result[0] == "VNM"
        assert result[1] == 72000

    def test_create_connection_in_memory(self) -> None:
        """Verify create_connection() initializes schema correctly."""
        conn = create_connection(":memory:")
        # Verify tables exist
        tables = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()
        table_names = [t[0] for t in tables]
        assert "ticks" in table_names
        assert "orders" in table_names


class TestDuckDBOrderRepository:
    """Integration tests for DuckDBOrderRepository."""

    def _make_order(self, order_id: str = "ORD-001") -> Order:
        now = datetime(2026, 2, 10, 10, 0, 0)
        return Order(
            order_id=order_id,
            symbol=Symbol("FPT"),
            side=OrderSide.BUY,
            order_type=OrderType.LO,
            quantity=Quantity(1000),
            price=Price(Decimal("98500")),
            ceiling_price=Price(Decimal("105400")),
            floor_price=Price(Decimal("91600")),
            status=OrderStatus.CREATED,
            filled_quantity=Quantity(0),
            avg_fill_price=Price(Decimal("0")),
            broker_order_id=None,
            rejection_reason=None,
            idempotency_key=f"IDEM-{order_id}",
            created_at=now,
            updated_at=now,
        )

    @pytest.mark.asyncio
    async def test_save_and_get_by_id(self, duckdb_conn: duckdb.DuckDBPyConnection) -> None:
        repo = DuckDBOrderRepository(duckdb_conn)
        order = self._make_order()
        await repo.save(order)

        retrieved = await repo.get_by_id("ORD-001")
        assert retrieved is not None
        assert retrieved.order_id == "ORD-001"
        assert retrieved.symbol == "FPT"
        assert retrieved.status == OrderStatus.CREATED

    @pytest.mark.asyncio
    async def test_save_update_existing(self, duckdb_conn: duckdb.DuckDBPyConnection) -> None:
        repo = DuckDBOrderRepository(duckdb_conn)
        order = self._make_order()
        await repo.save(order)

        # Update status
        updated = order.transition_to(OrderStatus.PENDING)
        await repo.save(updated)

        retrieved = await repo.get_by_id("ORD-001")
        assert retrieved is not None
        assert retrieved.status == OrderStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_by_symbol(self, duckdb_conn: duckdb.DuckDBPyConnection) -> None:
        repo = DuckDBOrderRepository(duckdb_conn)
        await repo.save(self._make_order("ORD-001"))
        await repo.save(self._make_order("ORD-002"))

        orders = await repo.get_by_symbol(Symbol("FPT"))
        assert len(orders) == 2

    @pytest.mark.asyncio
    async def test_get_open_orders(self, duckdb_conn: duckdb.DuckDBPyConnection) -> None:
        repo = DuckDBOrderRepository(duckdb_conn)

        # Save one CREATED and one MATCHED order
        await repo.save(self._make_order("ORD-001"))

        matched_order = self._make_order("ORD-002")
        matched_order = matched_order.transition_to(OrderStatus.PENDING)
        matched_order = matched_order.transition_to(OrderStatus.MATCHED)
        await repo.save(matched_order)

        open_orders = await repo.get_open_orders()
        assert len(open_orders) == 1
        assert open_orders[0].order_id == "ORD-001"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, duckdb_conn: duckdb.DuckDBPyConnection) -> None:
        repo = DuckDBOrderRepository(duckdb_conn)
        result = await repo.get_by_id("NONEXISTENT")
        assert result is None
