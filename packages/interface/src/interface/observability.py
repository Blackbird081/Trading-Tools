from __future__ import annotations

import uuid
from collections import deque
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from interface.redaction import redact_text

_CORRELATION_ID = ContextVar("interface_correlation_id", default="")
_EVENTS_LOCK = Lock()
_EVENTS: deque[dict[str, Any]] = deque(maxlen=400)


def get_correlation_id() -> str:
    value = _CORRELATION_ID.get().strip()
    return value or "unknown"


def ensure_correlation_id() -> str:
    value = _CORRELATION_ID.get().strip()
    if value:
        return value
    value = str(uuid.uuid4())
    _CORRELATION_ID.set(value)
    return value


def set_correlation_id(value: str) -> Token[str]:
    cleaned = value.strip() or str(uuid.uuid4())
    return _CORRELATION_ID.set(cleaned)


def reset_correlation_id(token: Token[str]) -> None:
    _CORRELATION_ID.reset(token)


def record_event(
    *,
    flow: str,
    level: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    event = {
        "timestamp": datetime.now(UTC).isoformat(),
        "correlation_id": get_correlation_id(),
        "flow": flow,
        "level": level.lower(),
        "message": redact_text(message),
        "metadata": metadata or {},
    }
    with _EVENTS_LOCK:
        _EVENTS.append(event)


def list_events(*, flow: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    limited = max(1, min(limit, 400))
    with _EVENTS_LOCK:
        items = list(_EVENTS)
    if flow:
        flow_norm = flow.strip().lower()
        items = [item for item in items if str(item.get("flow", "")).lower() == flow_norm]
    return list(reversed(items))[:limited]

