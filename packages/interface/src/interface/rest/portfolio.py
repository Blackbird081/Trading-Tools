from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter
from fastapi import Query

from interface.live_broker import create_ssi_portfolio_client, live_broker_enabled
from interface.observability import get_correlation_id, record_event
from interface.redaction import redact_text
from interface.trading_store import (
    compute_portfolio,
    get_conn,
    get_trading_mode,
    portfolio_pnl_series,
    save_portfolio_snapshot,
)

router = APIRouter(tags=["portfolio"])


def _as_float(value: Decimal | float | int) -> float:
    return float(Decimal(str(value)))


def _serialize_live_portfolio(snapshot: Any) -> dict[str, object]:
    positions = [
        {
            "symbol": str(position.symbol),
            "quantity": int(position.quantity),
            "sellable_qty": int(position.sellable_qty),
            "receiving_t1": int(position.receiving_t1),
            "receiving_t2": int(position.receiving_t2),
            "avg_price": _as_float(position.avg_price),
            "market_price": _as_float(position.market_price),
            "market_value": _as_float(position.market_value),
            "unrealized_pnl": _as_float(position.unrealized_pnl),
            "unrealized_pnl_pct": _as_float(position.unrealized_pnl_pct),
        }
        for position in snapshot.positions
    ]
    unrealized = sum(_as_float(position.unrealized_pnl) for position in snapshot.positions)
    return {
        "mode": "live",
        "source": "broker",
        "cash": _as_float(snapshot.cash.cash_bal),
        "purchasing_power": _as_float(snapshot.cash.purchasing_power),
        "pending_settlement": _as_float(snapshot.cash.pending_settlement),
        "nav": _as_float(snapshot.net_asset_value),
        "realized_pnl": 0.0,
        "unrealized_pnl": round(unrealized, 4),
        "positions": positions,
        "last_sync_at": snapshot.synced_at.isoformat(),
    }


async def _maybe_load_live_broker_portfolio() -> dict[str, object] | None:
    if not live_broker_enabled():
        return None
    client, auth = create_ssi_portfolio_client()
    try:
        state = await client.get_portfolio()
        return _serialize_live_portfolio(state)
    finally:
        await client.close()
        await auth.close()


async def _resolve_portfolio_snapshot() -> dict[str, object]:
    mode = get_trading_mode()
    if mode == "live":
        try:
            live_snapshot = await _maybe_load_live_broker_portfolio()
            if live_snapshot is not None:
                return live_snapshot
        except Exception as exc:
            safe_error = redact_text(str(exc))
            record_event(
                flow="portfolio",
                level="warn",
                message=f"Live broker portfolio fetch failed; fallback to cache: {safe_error}",
                metadata={"mode": "live"},
            )
            fallback = compute_portfolio(mode=mode)
            fallback["source"] = "dry-run-cache"
            fallback["broker_sync_error"] = safe_error
            return fallback
    snapshot = compute_portfolio(mode=mode)
    snapshot["source"] = "dry-run-cache" if mode == "dry-run" else "broker"
    return snapshot


@router.get("/portfolio")
async def get_portfolio() -> dict[str, object]:
    """Get current portfolio summary."""
    summary = await _resolve_portfolio_snapshot()
    return {
        "account_id": "local-personal",
        "mode": summary["mode"],
        "source": summary.get("source", "dry-run-cache"),
        "cash": summary["cash"],
        "nav": summary["nav"],
        "purchasing_power": summary["purchasing_power"],
        "realized_pnl": summary["realized_pnl"],
        "unrealized_pnl": summary["unrealized_pnl"],
        "pending_settlement": summary.get("pending_settlement", 0.0),
        "last_sync_at": summary["last_sync_at"],
        "broker_sync_error": summary.get("broker_sync_error"),
        "correlation_id": get_correlation_id(),
    }


@router.get("/portfolio/positions")
async def get_portfolio_positions() -> dict[str, object]:
    summary = await _resolve_portfolio_snapshot()
    return {
        "positions": summary.get("positions", []),
        "source": summary.get("source", "dry-run-cache"),
        "last_sync_at": summary["last_sync_at"],
        "correlation_id": get_correlation_id(),
    }


@router.get("/portfolio/pnl")
async def get_portfolio_pnl(days: int = Query(default=30, ge=1, le=365)) -> dict[str, object]:
    series = portfolio_pnl_series(days=days)
    return {"series": series, "days": days}


@router.post("/portfolio/refresh")
async def refresh_portfolio() -> dict[str, object]:
    mode = get_trading_mode()
    if mode == "live" and live_broker_enabled():
        summary = await _resolve_portfolio_snapshot()
    else:
        summary = save_portfolio_snapshot(mode=mode)
    return {
        "success": True,
        "mode": summary["mode"],
        "source": summary.get("source", "dry-run-cache"),
        "cash": summary["cash"],
        "nav": summary["nav"],
        "purchasing_power": summary["purchasing_power"],
        "last_sync_at": summary["last_sync_at"],
        "correlation_id": get_correlation_id(),
    }


@router.post("/portfolio/reconcile")
async def reconcile_portfolio() -> dict[str, object]:
    summary = await _resolve_portfolio_snapshot()
    if summary.get("source") == "broker":
        cached = compute_portfolio(mode="live")
        tolerance = 1e-3
        mismatches: list[str] = []
        if abs(float(cached["nav"]) - float(summary["nav"])) > tolerance:
            mismatches.append("nav")
        if abs(float(cached["cash"]) - float(summary["cash"])) > tolerance:
            mismatches.append("cash")
        if abs(float(cached["purchasing_power"]) - float(summary["purchasing_power"])) > tolerance:
            mismatches.append("purchasing_power")
        return {
            "success": True,
            "mode": "live",
            "source": "broker",
            "matched": len(mismatches) == 0,
            "mismatches": mismatches,
            "snapshot_at": summary["last_sync_at"],
            "checked_at": datetime.now(UTC).isoformat(),
            "correlation_id": get_correlation_id(),
        }

    conn = get_conn()
    latest = conn.execute(
        """
        SELECT nav, cash, purchasing_power, created_at
        FROM portfolio_snapshots
        ORDER BY created_at DESC
        LIMIT 1
        """,
    ).fetchone()
    if latest is None:
        return {
            "success": True,
            "status": "no_snapshot",
            "message": "No snapshot found; run /api/portfolio/refresh first.",
            "checked_at": datetime.now(UTC).isoformat(),
            "correlation_id": get_correlation_id(),
        }

    snapshot_nav = float(latest[0])
    snapshot_cash = float(latest[1])
    snapshot_power = float(latest[2])
    tolerance = 1e-3
    mismatches: list[str] = []
    if abs(snapshot_nav - float(summary["nav"])) > tolerance:
        mismatches.append("nav")
    if abs(snapshot_cash - float(summary["cash"])) > tolerance:
        mismatches.append("cash")
    if abs(snapshot_power - float(summary["purchasing_power"])) > tolerance:
        mismatches.append("purchasing_power")

    return {
        "success": True,
        "mode": get_trading_mode(),
        "source": summary.get("source", "dry-run-cache"),
        "matched": len(mismatches) == 0,
        "mismatches": mismatches,
        "snapshot_at": str(latest[3]),
        "checked_at": datetime.now(UTC).isoformat(),
        "correlation_id": get_correlation_id(),
    }
