from __future__ import annotations

from interface.redaction import REDACTED, redact_mapping, redact_text


def test_redact_text_masks_common_secret_patterns() -> None:
    raw = (
        "api_key=sk-1234567890 secret:abcd token=xyz "
        "Authorization=Bearer abcdefghijklmnop AIza1234567890example"
    )
    out = redact_text(raw)
    assert "sk-1234567890" not in out
    assert "abcdefghijklmno" not in out
    assert REDACTED in out


def test_redact_mapping_masks_sensitive_fields_recursively() -> None:
    payload = {
        "vnstock_api_key": "abc123",
        "nested": {"ssi_consumer_secret": "secret-value"},
        "notes": ["token=abc", "safe text"],
        "trading_mode": "dry-run",
    }
    redacted = redact_mapping(payload)
    assert redacted["vnstock_api_key"] == REDACTED
    assert redacted["nested"]["ssi_consumer_secret"] == REDACTED
    assert REDACTED in redacted["notes"][0]
    assert redacted["trading_mode"] == "dry-run"
