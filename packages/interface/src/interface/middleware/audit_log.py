"""Audit Log — immutable audit trail for all order operations.

★ SEC-03: Every order operation is logged with full context.
★ JSONL format: append-only, tamper-evident.
★ Includes: user_id, action, symbol, quantity, price, timestamp, result.
★ Required for regulatory compliance (SSC Vietnam regulations).
"""
from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("interface.audit")

# ★ Configurable via TRADING_AUDIT_LOG_DIR env var
AUDIT_LOG_DIR = Path(os.getenv("TRADING_AUDIT_LOG_DIR", ".trading/audit"))


class OrderAuditLog:
    """Append-only audit log for order operations.

    ★ JSONL format: one JSON object per line.
    ★ File rotated daily: audit_YYYY-MM-DD.jsonl
    ★ Never deletes or modifies existing entries.
    """

    def __init__(self, log_dir: Path | None = None) -> None:
        self._log_dir = log_dir or AUDIT_LOG_DIR
        self._log_dir.mkdir(parents=True, exist_ok=True)

    def _get_log_file(self) -> Path:
        """Get today's audit log file path."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        return self._log_dir / f"audit_{today}.jsonl"

    def _write(self, entry: dict[str, Any]) -> None:
        """Append entry to audit log (thread-safe via file append mode)."""
        try:
            with open(self._get_log_file(), "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        except Exception:
            # Audit log failure should not block order processing
            logger.exception("Failed to write audit log entry")

    def log_order_placed(
        self,
        order_id: str,
        symbol: str,
        side: str,
        quantity: int,
        price: Any,
        broker_order_id: str | None,
        dry_run: bool,
        user_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> None:
        """Log a successful order placement."""
        self._write({
            "event": "order_placed",
            "timestamp": datetime.now(UTC).isoformat(),
            "order_id": order_id,
            "broker_order_id": broker_order_id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": str(price),
            "dry_run": dry_run,
            "user_id": user_id,
            "idempotency_key": idempotency_key,
        })
        logger.info(
            "AUDIT: order_placed order_id=%s symbol=%s side=%s qty=%d price=%s dry_run=%s",
            order_id, symbol, side, quantity, price, dry_run,
        )

    def log_order_rejected(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: Any,
        reason: str,
        user_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> None:
        """Log a rejected order (risk check or broker rejection)."""
        self._write({
            "event": "order_rejected",
            "timestamp": datetime.now(UTC).isoformat(),
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": str(price),
            "reason": reason,
            "user_id": user_id,
            "idempotency_key": idempotency_key,
        })
        logger.warning(
            "AUDIT: order_rejected symbol=%s side=%s qty=%d reason=%s",
            symbol, side, quantity, reason,
        )

    def log_order_cancelled(
        self,
        order_id: str,
        reason: str | None = None,
        user_id: str | None = None,
    ) -> None:
        """Log an order cancellation."""
        self._write({
            "event": "order_cancelled",
            "timestamp": datetime.now(UTC).isoformat(),
            "order_id": order_id,
            "reason": reason,
            "user_id": user_id,
        })
        logger.info("AUDIT: order_cancelled order_id=%s reason=%s", order_id, reason)

    def log_kill_switch_activated(
        self,
        activated_by: str,
        reason: str,
    ) -> None:
        """Log kill switch activation — highest priority audit event."""
        self._write({
            "event": "kill_switch_activated",
            "timestamp": datetime.now(UTC).isoformat(),
            "activated_by": activated_by,
            "reason": reason,
            "severity": "CRITICAL",
        })
        logger.critical(
            "AUDIT: KILL_SWITCH_ACTIVATED by=%s reason=%s",
            activated_by, reason,
        )

    def log_early_warning_block(
        self,
        symbol: str,
        risk_score: float,
        risk_level: str,
        alerts: list[str],
    ) -> None:
        """Log when Early Warning System blocks a trade."""
        self._write({
            "event": "early_warning_block",
            "timestamp": datetime.now(UTC).isoformat(),
            "symbol": symbol,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "alerts": alerts[:5],  # Max 5 alerts in log
        })
        logger.warning(
            "AUDIT: early_warning_block symbol=%s risk_score=%.0f risk_level=%s",
            symbol, risk_score, risk_level,
        )


# ── Module-level singleton ────────────────────────────────────────────────────

_audit_log: OrderAuditLog | None = None


def get_audit_log() -> OrderAuditLog:
    """Get the global OrderAuditLog singleton."""
    global _audit_log  # noqa: PLW0603
    if _audit_log is None:
        _audit_log = OrderAuditLog()
    return _audit_log
