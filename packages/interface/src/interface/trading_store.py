from __future__ import annotations

import asyncio
import json
import os
import threading
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import duckdb
from adapters.duckdb.idempotency_store import DuckDBIdempotencyStore
from adapters.duckdb.telemetry import execute_with_trace

try:
    _LOCAL_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
except Exception:  # pragma: no cover - environment-specific tzdata availability
    _LOCAL_TZ = UTC
_SCHEMA_LOCK = threading.Lock()
_CONN: duckdb.DuckDBPyConnection | None = None
_IDEMPOTENCY: DuckDBIdempotencyStore | None = None


def get_db_path() -> Path:
    raw = os.getenv("DUCKDB_PATH", "data/trading.duckdb").strip()
    path = Path(raw).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_conn() -> duckdb.DuckDBPyConnection:
    global _CONN  # noqa: PLW0603
    if _CONN is None:
        with _SCHEMA_LOCK:
            if _CONN is None:
                _CONN = duckdb.connect(str(get_db_path()))
                _init_schema(_CONN)
    return _CONN


async def get_idempotency_store() -> DuckDBIdempotencyStore:
    global _IDEMPOTENCY  # noqa: PLW0603
    if _IDEMPOTENCY is None:
        _IDEMPOTENCY = await DuckDBIdempotencyStore.create(str(get_db_path()))
    return _IDEMPOTENCY


def _init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    execute_with_trace(
        conn,
        """
        CREATE TABLE IF NOT EXISTS orders (
            order_id         VARCHAR PRIMARY KEY,
            symbol           VARCHAR NOT NULL,
            side             VARCHAR NOT NULL,
            order_type       VARCHAR NOT NULL,
            quantity         INTEGER NOT NULL,
            req_price        DOUBLE NOT NULL,
            ceiling_price    DOUBLE NOT NULL,
            floor_price      DOUBLE NOT NULL,
            status           VARCHAR NOT NULL,
            filled_quantity  INTEGER DEFAULT 0,
            avg_fill_price   DOUBLE DEFAULT 0,
            broker_order_id  VARCHAR,
            rejection_reason VARCHAR,
            idempotency_key  VARCHAR NOT NULL,
            mode             VARCHAR NOT NULL DEFAULT 'dry-run',
            risk_summary     VARCHAR,
            created_at       TIMESTAMP NOT NULL,
            updated_at       TIMESTAMP NOT NULL
        )
        """,
    )
    execute_with_trace(
        conn,
        """
        CREATE TABLE IF NOT EXISTS order_audit (
            event_id      VARCHAR PRIMARY KEY,
            order_id      VARCHAR NOT NULL,
            event_type    VARCHAR NOT NULL,
            payload_json  VARCHAR NOT NULL,
            created_at    TIMESTAMP NOT NULL
        )
        """,
    )
    execute_with_trace(
        conn,
        """
        CREATE TABLE IF NOT EXISTS failed_orders_dlq (
            dlq_id          VARCHAR PRIMARY KEY,
            order_id        VARCHAR,
            payload_json    VARCHAR NOT NULL,
            error_message   VARCHAR NOT NULL,
            retry_count     INTEGER NOT NULL DEFAULT 0,
            max_retries     INTEGER NOT NULL DEFAULT 3,
            status          VARCHAR NOT NULL DEFAULT 'PENDING',
            next_retry_at   TIMESTAMP NOT NULL,
            last_retry_at   TIMESTAMP,
            resolved_at     TIMESTAMP,
            created_at      TIMESTAMP NOT NULL,
            updated_at      TIMESTAMP NOT NULL
        )
        """,
    )
    execute_with_trace(
        conn,
        """
        CREATE TABLE IF NOT EXISTS order_rejections (
            rejection_id    VARCHAR PRIMARY KEY,
            order_id        VARCHAR,
            reason          VARCHAR NOT NULL,
            created_at      TIMESTAMP NOT NULL
        )
        """,
    )
    execute_with_trace(
        conn,
        """
        CREATE TABLE IF NOT EXISTS portfolio_snapshots (
            snapshot_id       VARCHAR PRIMARY KEY,
            mode              VARCHAR NOT NULL,
            cash              DOUBLE NOT NULL,
            nav               DOUBLE NOT NULL,
            purchasing_power  DOUBLE NOT NULL,
            realized_pnl      DOUBLE NOT NULL DEFAULT 0,
            unrealized_pnl    DOUBLE NOT NULL DEFAULT 0,
            created_at        TIMESTAMP NOT NULL
        )
        """,
    )
    execute_with_trace(
        conn,
        """
        CREATE TABLE IF NOT EXISTS screener_runs (
            run_id           VARCHAR PRIMARY KEY,
            preset           VARCHAR NOT NULL,
            mode             VARCHAR NOT NULL,
            total_symbols    INTEGER NOT NULL,
            buy_count        INTEGER NOT NULL,
            sell_count       INTEGER NOT NULL,
            hold_count       INTEGER NOT NULL,
            avg_score        DOUBLE NOT NULL,
            metadata_json    VARCHAR NOT NULL,
            created_at       TIMESTAMP NOT NULL
        )
        """,
    )
    execute_with_trace(
        conn,
        """
        CREATE TABLE IF NOT EXISTS screener_run_results (
            result_id        VARCHAR PRIMARY KEY,
            run_id           VARCHAR NOT NULL,
            symbol           VARCHAR NOT NULL,
            action           VARCHAR NOT NULL,
            score            DOUBLE NOT NULL,
            confidence       DOUBLE NOT NULL,
            risk             VARCHAR NOT NULL,
            reasoning        VARCHAR NOT NULL,
            payload_json     VARCHAR NOT NULL,
            created_at       TIMESTAMP NOT NULL
        )
        """,
    )
    execute_with_trace(
        conn,
        """
        CREATE TABLE IF NOT EXISTS safety_state (
            key         VARCHAR PRIMARY KEY,
            value_json  VARCHAR NOT NULL,
            updated_at  TIMESTAMP NOT NULL
        )
        """,
    )


def now_utc() -> datetime:
    return datetime.now(UTC)


def now_local() -> datetime:
    return datetime.now(_LOCAL_TZ)


def get_trading_mode(preferred: str | None = None) -> str:
    if preferred in {"dry-run", "live"}:
        return preferred
    env_mode = os.getenv("TRADING_MODE", "").strip().lower()
    if env_mode in {"dry-run", "live"}:
        return env_mode
    dry = os.getenv("DRY_RUN", "true").strip().lower() in {"1", "true", "yes", "on"}
    return "dry-run" if dry else "live"


def market_session_open() -> bool:
    now = now_local()
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    morning_open = 9 * 60 <= minutes <= 11 * 60 + 30
    afternoon_open = 13 * 60 <= minutes <= 15 * 60
    return morning_open or afternoon_open


def get_safety_state(key: str, default: dict[str, Any] | None = None) -> dict[str, Any]:
    conn = get_conn()
    row = execute_with_trace(conn, "SELECT value_json FROM safety_state WHERE key = ?", [key]).fetchone()
    if row is None:
        return default or {}
    return json.loads(str(row[0]))


def set_safety_state(key: str, value: dict[str, Any]) -> None:
    conn = get_conn()
    execute_with_trace(
        conn,
        """
        INSERT INTO safety_state (key, value_json, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT (key) DO UPDATE SET
            value_json = excluded.value_json,
            updated_at = excluded.updated_at
        """,
        [key, json.dumps(value, ensure_ascii=False), now_utc()],
    )


def log_order_audit(order_id: str, event_type: str, payload: dict[str, Any]) -> None:
    conn = get_conn()
    execute_with_trace(
        conn,
        """
        INSERT INTO order_audit (event_id, order_id, event_type, payload_json, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        [str(uuid.uuid4()), order_id, event_type, json.dumps(payload, ensure_ascii=False), now_utc()],
    )


def record_order_rejection(order_id: str | None, reason: str) -> None:
    conn = get_conn()
    execute_with_trace(
        conn,
        """
        INSERT INTO order_rejections (rejection_id, order_id, reason, created_at)
        VALUES (?, ?, ?, ?)
        """,
        [str(uuid.uuid4()), order_id, reason, now_utc()],
    )


def recent_rejection_count(window_minutes: int = 10) -> int:
    conn = get_conn()
    since = now_utc() - timedelta(minutes=window_minutes)
    row = execute_with_trace(
        conn,
        "SELECT COUNT(*) FROM order_rejections WHERE created_at >= ?",
        [since],
    ).fetchone()
    return int(row[0]) if row else 0


def enqueue_dlq(order_id: str | None, payload: dict[str, Any], error_message: str, delay_seconds: int = 30) -> str:
    conn = get_conn()
    dlq_id = str(uuid.uuid4())
    now = now_utc()
    execute_with_trace(
        conn,
        """
        INSERT INTO failed_orders_dlq (
            dlq_id, order_id, payload_json, error_message, retry_count, max_retries,
            status, next_retry_at, last_retry_at, resolved_at, created_at, updated_at
        ) VALUES (?, ?, ?, ?, 0, 3, 'PENDING', ?, NULL, NULL, ?, ?)
        """,
        [dlq_id, order_id, json.dumps(payload, ensure_ascii=False), error_message, now + timedelta(seconds=delay_seconds), now, now],
    )
    return dlq_id


def list_dlq() -> list[dict[str, Any]]:
    conn = get_conn()
    rows = execute_with_trace(
        conn,
        """
        SELECT dlq_id, order_id, error_message, retry_count, max_retries, status, next_retry_at, created_at, updated_at
        FROM failed_orders_dlq
        ORDER BY created_at DESC
        """,
    ).fetchall()
    result: list[dict[str, Any]] = []
    for r in rows:
        result.append(
            {
                "dlq_id": str(r[0]),
                "order_id": str(r[1]) if r[1] is not None else None,
                "error_message": str(r[2]),
                "retry_count": int(r[3]),
                "max_retries": int(r[4]),
                "status": str(r[5]),
                "next_retry_at": str(r[6]),
                "created_at": str(r[7]),
                "updated_at": str(r[8]),
            }
        )
    return result


def _update_dlq_status(dlq_id: str, status: str, retry_count: int, error_message: str) -> None:
    conn = get_conn()
    now = now_utc()
    next_retry = now + timedelta(seconds=min(300, 30 * (2 ** min(retry_count, 4))))
    resolved_at = now if status == "RESOLVED" else None
    execute_with_trace(
        conn,
        """
        UPDATE failed_orders_dlq
        SET status = ?, retry_count = ?, error_message = ?, next_retry_at = ?, last_retry_at = ?, resolved_at = ?, updated_at = ?
        WHERE dlq_id = ?
        """,
        [status, retry_count, error_message, next_retry, now, resolved_at, now, dlq_id],
    )


def try_replay_dlq(dlq_id: str | None = None) -> list[dict[str, Any]]:
    conn = get_conn()
    if dlq_id:
        rows = execute_with_trace(
            conn,
            """
            SELECT dlq_id, payload_json, retry_count, max_retries
            FROM failed_orders_dlq
            WHERE dlq_id = ? AND status IN ('PENDING', 'RETRYING')
            """,
            [dlq_id],
        ).fetchall()
    else:
        rows = execute_with_trace(
            conn,
            """
            SELECT dlq_id, payload_json, retry_count, max_retries
            FROM failed_orders_dlq
            WHERE status IN ('PENDING', 'RETRYING') AND next_retry_at <= ?
            ORDER BY created_at ASC
            LIMIT 20
            """,
            [now_utc()],
        ).fetchall()

    replayed: list[dict[str, Any]] = []
    for row in rows:
        item_id = str(row[0])
        payload = json.loads(str(row[1]))
        retry_count = int(row[2]) + 1
        max_retries = int(row[3])

        # Current runtime only supports reliable auto-resolution for dry-run payloads.
        mode = str(payload.get("mode", "dry-run"))
        if mode == "dry-run":
            _update_dlq_status(item_id, "RESOLVED", retry_count, "Resolved in dry-run replay")
            replayed.append({"dlq_id": item_id, "status": "RESOLVED", "retry_count": retry_count})
            continue

        if retry_count >= max_retries:
            _update_dlq_status(item_id, "PERMANENT_FAILED", retry_count, "Max retries reached")
            replayed.append({"dlq_id": item_id, "status": "PERMANENT_FAILED", "retry_count": retry_count})
            continue

        _update_dlq_status(item_id, "RETRYING", retry_count, "Retry pending live broker availability")
        replayed.append({"dlq_id": item_id, "status": "RETRYING", "retry_count": retry_count})
    return replayed


class DLQRetryWorker:
    def __init__(self, interval_seconds: int = 20) -> None:
        self._interval_seconds = interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="dlq-retry-worker")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                try_replay_dlq()
            except Exception:
                # keep worker alive
                pass
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self._interval_seconds)
            except TimeoutError:
                continue


def upsert_order(order: dict[str, Any]) -> None:
    conn = get_conn()
    execute_with_trace(
        conn,
        """
        INSERT INTO orders (
            order_id, symbol, side, order_type, quantity, req_price,
            ceiling_price, floor_price, status, filled_quantity,
            avg_fill_price, broker_order_id, rejection_reason,
            idempotency_key, mode, risk_summary, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (order_id) DO UPDATE SET
            status = excluded.status,
            filled_quantity = excluded.filled_quantity,
            avg_fill_price = excluded.avg_fill_price,
            broker_order_id = excluded.broker_order_id,
            rejection_reason = excluded.rejection_reason,
            mode = excluded.mode,
            risk_summary = excluded.risk_summary,
            updated_at = excluded.updated_at
        """,
        [
            order["order_id"],
            order["symbol"],
            order["side"],
            order["order_type"],
            int(order["quantity"]),
            float(order["req_price"]),
            float(order["ceiling_price"]),
            float(order["floor_price"]),
            order["status"],
            int(order.get("filled_quantity", 0)),
            float(order.get("avg_fill_price", order["req_price"])),
            order.get("broker_order_id"),
            order.get("rejection_reason"),
            order["idempotency_key"],
            order.get("mode", "dry-run"),
            json.dumps(order.get("risk_summary", {}), ensure_ascii=False),
            order.get("created_at", now_utc()),
            order.get("updated_at", now_utc()),
        ],
    )


def get_order(order_id: str) -> dict[str, Any] | None:
    conn = get_conn()
    row = execute_with_trace(conn, "SELECT * FROM orders WHERE order_id = ?", [order_id]).fetchone()
    if row is None:
        return None
    return _map_order_row(row)


def list_orders(limit: int = 200, status: str | None = None, symbol: str | None = None) -> list[dict[str, Any]]:
    conn = get_conn()
    sql = "SELECT * FROM orders WHERE 1=1"
    params: list[Any] = []
    if status:
        sql += " AND status = ?"
        params.append(status)
    if symbol:
        sql += " AND symbol = ?"
        params.append(symbol.upper())
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = execute_with_trace(conn, sql, params).fetchall()
    return [_map_order_row(r) for r in rows]


def set_order_status(order_id: str, status: str, reason: str | None = None) -> dict[str, Any] | None:
    existing = get_order(order_id)
    if existing is None:
        return None
    existing["status"] = status
    existing["rejection_reason"] = reason
    existing["updated_at"] = now_utc().isoformat()
    upsert_order(existing)
    log_order_audit(order_id, "status_changed", {"status": status, "reason": reason})
    return get_order(order_id)


def _map_order_row(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "order_id": str(row[0]),
        "symbol": str(row[1]),
        "side": str(row[2]),
        "order_type": str(row[3]),
        "quantity": int(row[4]),
        "req_price": float(row[5]),
        "ceiling_price": float(row[6]),
        "floor_price": float(row[7]),
        "status": str(row[8]),
        "filled_quantity": int(row[9]),
        "avg_fill_price": float(row[10]),
        "broker_order_id": str(row[11]) if row[11] is not None else None,
        "rejection_reason": str(row[12]) if row[12] is not None else None,
        "idempotency_key": str(row[13]),
        "mode": str(row[14]) if len(row) > 14 and row[14] is not None else "dry-run",
        "risk_summary": json.loads(str(row[15])) if len(row) > 15 and row[15] is not None else {},
        "created_at": str(row[16]),
        "updated_at": str(row[17]),
    }


def latest_price(symbol: str) -> float:
    conn = get_conn()
    try:
        row = execute_with_trace(
            conn,
            """
            SELECT price FROM market_cache
            WHERE symbol = ?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            [symbol.upper()],
        ).fetchone()
    except Exception:
        return 0.0
    if row is None:
        return 0.0
    return float(row[0])


def reference_prices(symbol: str, fallback_price: float) -> tuple[float, float, float]:
    conn = get_conn()
    try:
        row = execute_with_trace(
            conn,
            """
            SELECT reference, ceiling, floor FROM market_cache
            WHERE symbol = ?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            [symbol.upper()],
        ).fetchone()
    except Exception:
        row = None
    if row is None:
        ref = fallback_price if fallback_price > 0 else 10000.0
        return ref, ref * 1.07, ref * 0.93
    return float(row[0]), float(row[1]), float(row[2])


def compute_portfolio(mode: str | None = None) -> dict[str, Any]:
    current_mode = get_trading_mode(mode)
    orders = list_orders(limit=5000)
    initial_cash = float(os.getenv("DRYRUN_INITIAL_CASH", "1000000000"))
    cash = initial_cash
    holdings: dict[str, dict[str, float]] = {}
    realized_pnl = 0.0

    for order in reversed(orders):
        status = str(order["status"])
        if status not in {"MATCHED", "PENDING", "PARTIAL_FILL"}:
            continue
        symbol = str(order["symbol"])
        qty = float(order["filled_quantity"] if order["filled_quantity"] > 0 else order["quantity"])
        price = float(order["avg_fill_price"] if order["avg_fill_price"] > 0 else order["req_price"])
        side = str(order["side"])
        pos = holdings.setdefault(symbol, {"qty": 0.0, "cost": 0.0})

        if side == "BUY":
            cash -= qty * price
            pos["cost"] += qty * price
            pos["qty"] += qty
        elif side == "SELL":
            sell_qty = min(qty, pos["qty"])
            if pos["qty"] > 0:
                avg_cost = pos["cost"] / pos["qty"]
            else:
                avg_cost = price
            realized_pnl += (price - avg_cost) * sell_qty
            cash += qty * price
            pos["qty"] = max(0.0, pos["qty"] - qty)
            pos["cost"] = max(0.0, pos["qty"] * avg_cost)

    positions: list[dict[str, Any]] = []
    unrealized_pnl = 0.0
    total_market_value = 0.0

    for symbol, data in sorted(holdings.items()):
        qty = data["qty"]
        if qty <= 0:
            continue
        avg_price = data["cost"] / qty if qty > 0 else 0.0
        market_price = latest_price(symbol) or avg_price
        pnl = (market_price - avg_price) * qty
        pnl_pct = ((market_price - avg_price) / avg_price * 100) if avg_price > 0 else 0.0
        unrealized_pnl += pnl
        total_market_value += market_price * qty
        positions.append(
            {
                "symbol": symbol,
                "quantity": int(qty),
                "sellable_qty": int(qty),
                "avg_price": round(avg_price, 4),
                "market_price": round(market_price, 4),
                "unrealized_pnl": round(pnl, 4),
                "unrealized_pnl_pct": round(pnl_pct, 4),
            }
        )

    nav = cash + total_market_value
    purchasing_power = max(cash, 0.0)
    summary = {
        "mode": current_mode,
        "cash": round(cash, 4),
        "nav": round(nav, 4),
        "purchasing_power": round(purchasing_power, 4),
        "realized_pnl": round(realized_pnl, 4),
        "unrealized_pnl": round(unrealized_pnl, 4),
        "positions": positions,
        "last_sync_at": now_utc().isoformat(),
    }
    return summary


def save_portfolio_snapshot(mode: str | None = None) -> dict[str, Any]:
    summary = compute_portfolio(mode=mode)
    conn = get_conn()
    execute_with_trace(
        conn,
        """
        INSERT INTO portfolio_snapshots (
            snapshot_id, mode, cash, nav, purchasing_power, realized_pnl, unrealized_pnl, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            str(uuid.uuid4()),
            summary["mode"],
            summary["cash"],
            summary["nav"],
            summary["purchasing_power"],
            summary["realized_pnl"],
            summary["unrealized_pnl"],
            now_utc(),
        ],
    )
    return summary


def portfolio_pnl_series(days: int = 30) -> list[dict[str, Any]]:
    conn = get_conn()
    rows = execute_with_trace(
        conn,
        """
        SELECT DATE(created_at) AS d, ANY_VALUE(nav) AS nav, ANY_VALUE(realized_pnl + unrealized_pnl) AS pnl
        FROM portfolio_snapshots
        WHERE created_at >= ?
        GROUP BY d
        ORDER BY d ASC
        """,
        [now_utc() - timedelta(days=max(1, days))],
    ).fetchall()
    series = []
    for row in rows:
        series.append(
            {
                "date": str(row[0]),
                "nav": float(row[1]),
                "pnl": float(row[2]),
            }
        )
    if not series:
        current = compute_portfolio()
        today = now_local().date().isoformat()
        series.append({"date": today, "nav": current["nav"], "pnl": current["realized_pnl"] + current["unrealized_pnl"]})
    return series


def save_screener_run(
    run_id: str,
    preset: str,
    mode: str,
    results: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> None:
    conn = get_conn()
    buy_count = sum(1 for r in results if str(r.get("action")) == "BUY")
    sell_count = sum(1 for r in results if str(r.get("action")) == "SELL")
    hold_count = sum(1 for r in results if str(r.get("action")) == "HOLD")
    avg_score = (sum(float(r.get("score", 0)) for r in results) / len(results)) if results else 0.0
    execute_with_trace(
        conn,
        """
        INSERT INTO screener_runs (
            run_id, preset, mode, total_symbols, buy_count, sell_count, hold_count, avg_score, metadata_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (run_id) DO UPDATE SET
            total_symbols = excluded.total_symbols,
            buy_count = excluded.buy_count,
            sell_count = excluded.sell_count,
            hold_count = excluded.hold_count,
            avg_score = excluded.avg_score,
            metadata_json = excluded.metadata_json,
            created_at = excluded.created_at
        """,
        [run_id, preset, mode, len(results), buy_count, sell_count, hold_count, avg_score, json.dumps(metadata, ensure_ascii=False), now_utc()],
    )
    for item in results:
        execute_with_trace(
            conn,
            """
            INSERT INTO screener_run_results (
                result_id, run_id, symbol, action, score, confidence, risk, reasoning, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                str(uuid.uuid4()),
                run_id,
                str(item.get("symbol", "")),
                str(item.get("action", "HOLD")),
                float(item.get("score", 0)),
                float(item.get("confidence", 0)),
                str(item.get("risk", "MEDIUM")),
                str(item.get("reasoning", "")),
                json.dumps(item, ensure_ascii=False),
                now_utc(),
            ],
        )


def screener_history(limit: int = 20) -> list[dict[str, Any]]:
    conn = get_conn()
    rows = execute_with_trace(
        conn,
        """
        SELECT run_id, preset, mode, total_symbols, buy_count, sell_count, hold_count, avg_score, metadata_json, created_at
        FROM screener_runs
        ORDER BY created_at DESC
        LIMIT ?
        """,
        [limit],
    ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "run_id": str(r[0]),
                "preset": str(r[1]),
                "mode": str(r[2]),
                "total_symbols": int(r[3]),
                "buy_count": int(r[4]),
                "sell_count": int(r[5]),
                "hold_count": int(r[6]),
                "avg_score": float(r[7]),
                "metadata": json.loads(str(r[8])) if r[8] else {},
                "created_at": str(r[9]),
            }
        )
    return out
