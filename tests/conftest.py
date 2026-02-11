"""Shared test fixtures — DuckDB in-memory, domain entities, risk limits.

★ DuckDB in-memory per test — zero disk I/O, instant teardown.
★ Domain fixtures are realistic but deterministic.

Ref: Doc 02 §5.2
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import duckdb
import pytest
from core.entities.order import Order, OrderSide, OrderStatus, OrderType
from core.entities.portfolio import CashBalance, PortfolioState, Position
from core.entities.risk import RiskLimit
from core.entities.tick import Exchange, Tick
from core.value_objects import Price, Quantity, Symbol

# ─── DuckDB In-Memory ───────────────────────────────────────


@pytest.fixture
def duckdb_conn() -> duckdb.DuckDBPyConnection:
    """Fresh in-memory DuckDB per test — zero disk I/O, instant teardown."""
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE ticks (
            symbol   VARCHAR,
            price    DOUBLE,
            volume   BIGINT,
            exchange VARCHAR,
            ts       TIMESTAMP
        );
        CREATE TABLE orders (
            order_id        VARCHAR,
            symbol          VARCHAR,
            side            VARCHAR,
            order_type      VARCHAR,
            quantity        INTEGER,
            req_price       DOUBLE,
            ceiling_price   DOUBLE,
            floor_price     DOUBLE,
            status          VARCHAR,
            filled_quantity INTEGER DEFAULT 0,
            avg_fill_price  DOUBLE DEFAULT 0,
            broker_order_id VARCHAR,
            rejection_reason VARCHAR,
            idempotency_key VARCHAR,
            created_at      TIMESTAMP,
            updated_at      TIMESTAMP
        );
    """)
    return conn


# ─── Domain Fixtures ─────────────────────────────────────────


@pytest.fixture
def sample_ticks() -> list[Tick]:
    """50 sample ticks for FPT on HOSE."""
    from datetime import timedelta

    base = datetime(2026, 2, 10, 9, 0, 0)
    return [
        Tick(
            symbol=Symbol("FPT"),
            price=Price(Decimal("98500")),
            volume=Quantity(1000),
            exchange=Exchange.HOSE,
            timestamp=base + timedelta(seconds=i),
        )
        for i in range(50)
    ]


@pytest.fixture
def sample_portfolio() -> PortfolioState:
    """Portfolio with 1 position and cash balance."""
    return PortfolioState(
        positions=(
            Position(
                symbol=Symbol("FPT"),
                quantity=Quantity(2000),
                sellable_qty=Quantity(1000),  # T+2.5: only 1000 settled
                receiving_t1=Quantity(500),
                receiving_t2=Quantity(500),
                avg_price=Price(Decimal("95000")),
                market_price=Price(Decimal("98500")),
            ),
        ),
        cash=CashBalance(
            cash_bal=Decimal("50000000"),
            purchasing_power=Decimal("80000000"),
            pending_settlement=Decimal("10000000"),
        ),
        synced_at=datetime(2026, 2, 10, 9, 30, 0),
    )


@pytest.fixture
def default_risk_limits() -> RiskLimit:
    """Standard risk limits for testing."""
    return RiskLimit(
        max_position_pct=Decimal("0.20"),  # 20% NAV per order
        max_daily_loss=Decimal("5000000"),
        kill_switch_active=False,
    )


@pytest.fixture
def sample_buy_order() -> Order:
    """Sample buy order for testing."""
    now = datetime(2026, 2, 10, 10, 0, 0)
    return Order(
        order_id="ORD-001",
        symbol=Symbol("VNM"),
        side=OrderSide.BUY,
        order_type=OrderType.LO,
        quantity=Quantity(500),
        price=Price(Decimal("72000")),
        ceiling_price=Price(Decimal("77000")),
        floor_price=Price(Decimal("67000")),
        status=OrderStatus.CREATED,
        filled_quantity=Quantity(0),
        avg_fill_price=Price(Decimal("0")),
        broker_order_id=None,
        rejection_reason=None,
        idempotency_key="IDEM-001",
        created_at=now,
        updated_at=now,
    )
