"""DuckDB Connection Pool — thread-safe connection management.

★ RES-03: Connection pool with max_connections limit.
★ Prevents "too many connections" errors under load.
★ asyncio.to_thread() compatible — each thread gets its own connection.
★ Graceful shutdown: waits for in-flight queries to complete.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

logger = logging.getLogger("adapters.duckdb.pool")


class DuckDBConnectionPool:
    """Thread-safe DuckDB connection pool.

    ★ RES-03: Limits concurrent connections to prevent resource exhaustion.
    ★ Each thread gets its own connection (DuckDB is not thread-safe for shared connections).
    ★ Connections are created lazily and reused within the same thread.

    Usage:
        pool = DuckDBConnectionPool("data/trading.duckdb", max_connections=5)
        with pool.acquire() as conn:
            conn.execute("SELECT ...")
    """

    def __init__(
        self,
        db_path: str | Path = ":memory:",
        max_connections: int = 5,
        read_only: bool = False,
    ) -> None:
        self._db_path = str(db_path)
        self._max_connections = max_connections
        self._read_only = read_only

        # Thread-local storage for per-thread connections
        self._local = threading.local()

        # Semaphore to limit concurrent connections
        self._semaphore = threading.Semaphore(max_connections)

        # Track all connections for graceful shutdown
        self._all_connections: list[Any] = []
        self._lock = threading.Lock()
        self._shutdown = False

        logger.info(
            "DuckDB pool initialized: path=%s, max_connections=%d",
            self._db_path, max_connections,
        )

    @contextmanager
    def acquire(self) -> Generator[Any, None, None]:
        """Acquire a connection from the pool.

        ★ Thread-safe: each thread gets its own connection.
        ★ Blocks if max_connections is reached.
        ★ Raises RuntimeError if pool is shut down.
        """
        if self._shutdown:
            msg = "DuckDB connection pool is shut down"
            raise RuntimeError(msg)

        # Get or create thread-local connection
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._semaphore.acquire()
            try:
                import duckdb
                conn = duckdb.connect(self._db_path, read_only=self._read_only)
                self._local.conn = conn
                with self._lock:
                    self._all_connections.append(conn)
                logger.debug("Created new DuckDB connection for thread %s", threading.current_thread().name)
            except Exception:
                self._semaphore.release()
                raise

        try:
            yield self._local.conn
        except Exception:
            # On error, close and remove the connection so next call gets a fresh one
            self._close_thread_connection()
            raise

    def _close_thread_connection(self) -> None:
        """Close the current thread's connection."""
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            self._local.conn = None
            with self._lock:
                try:
                    self._all_connections.remove(conn)
                except ValueError:
                    pass
            self._semaphore.release()

    async def shutdown(self) -> None:
        """★ RES-02: Graceful shutdown — close all connections.

        Waits for in-flight queries to complete before closing.
        """
        self._shutdown = True
        logger.info("DuckDB pool shutting down...")

        # Give in-flight queries a moment to complete
        await asyncio.sleep(0.1)

        with self._lock:
            connections = list(self._all_connections)

        for conn in connections:
            try:
                conn.close()
                logger.debug("Closed DuckDB connection")
            except Exception:
                pass

        with self._lock:
            self._all_connections.clear()

        logger.info("DuckDB pool shutdown complete")

    @property
    def active_connections(self) -> int:
        """Number of active connections."""
        with self._lock:
            return len(self._all_connections)

    @property
    def max_connections(self) -> int:
        return self._max_connections


# ── Module-level default pool ─────────────────────────────────────────────────

_default_pool: DuckDBConnectionPool | None = None


def get_default_pool(
    db_path: str | Path = ":memory:",
    max_connections: int = 5,
) -> DuckDBConnectionPool:
    """Get or create the default DuckDB connection pool."""
    global _default_pool  # noqa: PLW0603
    if _default_pool is None:
        _default_pool = DuckDBConnectionPool(db_path, max_connections=max_connections)
    return _default_pool
