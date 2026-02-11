"""DuckDB connection factory and lifecycle management.

★ Single connection per process (DuckDB is embedded, single-writer).
★ In-memory mode for tests (:memory:), file mode for production.

Ref: Doc 02 §2.5
"""

from __future__ import annotations

from pathlib import Path

import duckdb

# ── Schema DDL ────────────────────────────────────────────────

_SCHEMA_DDL = """
-- Bảng ticks: giá thị trường liên tục (hàng triệu rows/ngày)
CREATE TABLE IF NOT EXISTS ticks (
    symbol   VARCHAR NOT NULL,
    price    DOUBLE  NOT NULL,
    volume   BIGINT  NOT NULL,
    exchange VARCHAR NOT NULL,
    ts       TIMESTAMP NOT NULL
);

-- Bảng orders: lệnh giao dịch
CREATE TABLE IF NOT EXISTS orders (
    order_id        VARCHAR   NOT NULL,
    symbol          VARCHAR   NOT NULL,
    side            VARCHAR   NOT NULL,
    order_type      VARCHAR   NOT NULL,
    quantity        INTEGER   NOT NULL,
    req_price       DOUBLE    NOT NULL,
    ceiling_price   DOUBLE    NOT NULL,
    floor_price     DOUBLE    NOT NULL,
    status          VARCHAR   NOT NULL,
    filled_quantity INTEGER   NOT NULL DEFAULT 0,
    avg_fill_price  DOUBLE    NOT NULL DEFAULT 0,
    broker_order_id VARCHAR,
    rejection_reason VARCHAR,
    idempotency_key VARCHAR   NOT NULL,
    created_at      TIMESTAMP NOT NULL,
    updated_at      TIMESTAMP NOT NULL
);

-- Index for common queries
CREATE INDEX IF NOT EXISTS idx_ticks_symbol_ts ON ticks(symbol, ts);
CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_idempotency ON orders(idempotency_key);
"""


def create_connection(
    db_path: str | Path = ":memory:",
) -> duckdb.DuckDBPyConnection:
    """Create a DuckDB connection with schema initialized.

    Args:
        db_path: Path to database file, or ":memory:" for in-memory.

    Returns:
        Initialized DuckDB connection with schema applied.
    """
    db_path_str = str(db_path)

    # Ensure parent directory exists for file-based DB
    if db_path_str != ":memory:":
        Path(db_path_str).parent.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(db_path_str)
    conn.execute(_SCHEMA_DDL)
    return conn
