"""DuckDB-backed IdempotencyStore — persistent across restarts."""
from __future__ import annotations
import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
import duckdb

logger = logging.getLogger("oms.idempotency")

_DDL = """
CREATE TABLE IF NOT EXISTS idempotency_keys (
    key VARCHAR NOT NULL PRIMARY KEY,
    result_json VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_idempotency_expires ON idempotency_keys(expires_at);
"""


class DuckDBIdempotencyStore:
    """Persistent idempotency store backed by DuckDB."""

    def __init__(self, conn: duckdb.DuckDBPyConnection, max_age_hours: int = 24) -> None:
        self._conn = conn
        self._max_age_hours = max_age_hours
        self._conn.execute(_DDL)

    async def check(self, key: str) -> dict[str, object] | None:
        return await asyncio.to_thread(self._check_sync, key)

    def _check_sync(self, key: str) -> dict[str, object] | None:
        now = datetime.now(UTC)
        row = self._conn.execute(
            "SELECT result_json FROM idempotency_keys WHERE key = ? AND expires_at > ?",
            [key, now.isoformat()],
        ).fetchone()
        if row is None:
            return None
        return json.loads(str(row[0]))  # type: ignore[no-any-return]

    async def record(self, key: str, result: dict[str, object]) -> None:
        await asyncio.to_thread(self._record_sync, key, result)

    def _record_sync(self, key: str, result: dict[str, object]) -> None:
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=self._max_age_hours)
        # ★ DuckDB UPSERT (not SQLite's INSERT OR REPLACE)
        self._conn.execute(
            """
            INSERT INTO idempotency_keys (key, result_json, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (key) DO UPDATE SET
                result_json = excluded.result_json,
                expires_at  = excluded.expires_at
            """,
            [key, json.dumps(result), now.isoformat(), expires_at.isoformat()],
        )

    async def prune_expired(self) -> int:
        return await asyncio.to_thread(self._prune_expired_sync)

    def _prune_expired_sync(self) -> int:
        now = datetime.now(UTC)
        result = self._conn.execute(
            "SELECT COUNT(*) FROM idempotency_keys WHERE expires_at <= ?",
            [now.isoformat()],
        ).fetchone()
        count = int(result[0]) if result else 0
        if count > 0:
            self._conn.execute(
                "DELETE FROM idempotency_keys WHERE expires_at <= ?",
                [now.isoformat()],
            )
        return count
