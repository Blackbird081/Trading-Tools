from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

REDACTED = "***REDACTED***"

_SENSITIVE_KEYWORDS = (
    "api_key",
    "secret",
    "passphrase",
    "token",
    "private_key",
    "authorization",
)

_KV_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|secret|passphrase|token|private[_-]?key|authorization)\b\s*[:=]\s*(Bearer\s+[^\s,;]+|[^\s,;]+)"
)
_BEARER_PATTERN = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-+/=]+")
_KEYLIKE_PATTERN = re.compile(r"\b(sk-[A-Za-z0-9_\-]{8,}|AIza[A-Za-z0-9_\-]{10,})\b")


def redact_text(value: str) -> str:
    """Redact common secret patterns from free-form text."""
    redacted = _KV_PATTERN.sub(lambda m: f"{m.group(1)}={REDACTED}", value)
    redacted = _BEARER_PATTERN.sub(f"Bearer {REDACTED}", redacted)
    redacted = _KEYLIKE_PATTERN.sub(REDACTED, redacted)
    return redacted


def _is_sensitive_key(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_")
    return any(token in normalized for token in _SENSITIVE_KEYWORDS)


def redact_mapping(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Redact values under sensitive keys recursively."""
    out: dict[str, Any] = {}
    for key, value in payload.items():
        if _is_sensitive_key(str(key)):
            out[str(key)] = REDACTED if str(value).strip() else ""
            continue
        if isinstance(value, Mapping):
            out[str(key)] = redact_mapping(value)
            continue
        if isinstance(value, list):
            items: list[Any] = []
            for item in value:
                if isinstance(item, Mapping):
                    items.append(redact_mapping(item))
                elif isinstance(item, str):
                    items.append(redact_text(item))
                else:
                    items.append(item)
            out[str(key)] = items
            continue
        if isinstance(value, str):
            out[str(key)] = redact_text(value)
            continue
        out[str(key)] = value
    return out
