"""DuckDB tracing helpers (OpenTelemetry optional).

When OpenTelemetry is not installed/configured, these helpers degrade to no-op.
"""
from __future__ import annotations

import time
from collections.abc import Sequence
from typing import Any

try:  # pragma: no cover - optional dependency
    from opentelemetry import trace
except Exception:  # pragma: no cover - optional dependency
    trace = None  # type: ignore[assignment]


def _query_type(sql: str) -> str:
    parts = sql.strip().split(maxsplit=1)
    if not parts:
        return "UNKNOWN"
    return parts[0].upper()


def _set_span_attrs(span: Any, *, sql: str, params: Sequence[Any] | None = None) -> None:
    span.set_attribute("db.system", "duckdb")
    span.set_attribute("db.operation", _query_type(sql))
    span.set_attribute("db.statement", sql.strip()[:512])
    span.set_attribute("db.params_count", len(params) if params is not None else 0)


def execute_with_trace(
    conn: Any,
    sql: str,
    params: Sequence[Any] | None = None,
) -> Any:
    """Execute SQL with optional OpenTelemetry span."""
    if trace is None:
        return conn.execute(sql, params) if params is not None else conn.execute(sql)

    tracer = trace.get_tracer("adapters.duckdb")
    start = time.perf_counter()
    with tracer.start_as_current_span("duckdb.query") as span:
        _set_span_attrs(span, sql=sql, params=params)
        try:
            cursor = conn.execute(sql, params) if params is not None else conn.execute(sql)
            elapsed_ms = (time.perf_counter() - start) * 1000
            span.set_attribute("db.duration_ms", round(elapsed_ms, 3))
            span.set_status(trace.Status(trace.StatusCode.OK))
            return cursor
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            span.set_attribute("db.duration_ms", round(elapsed_ms, 3))
            span.set_attribute("db.error", True)
            span.record_exception(exc)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
            raise

