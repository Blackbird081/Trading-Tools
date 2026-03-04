from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter
from fastapi import Query

from interface.trading_store import (
    compute_portfolio,
    get_conn,
    get_trading_mode,
    portfolio_pnl_series,
    save_portfolio_snapshot,
)

router = APIRouter(tags=["portfolio"])


@router.get("/portfolio")
async def get_portfolio() -> dict[str, object]:
    """Get current portfolio summary."""
    summary = compute_portfolio()
    return {
        "account_id": "local-personal",
        "mode": summary["mode"],
        "cash": summary["cash"],
        "nav": summary["nav"],
        "purchasing_power": summary["purchasing_power"],
        "realized_pnl": summary["realized_pnl"],
        "unrealized_pnl": summary["unrealized_pnl"],
        "last_sync_at": summary["last_sync_at"],
    }


@router.get("/portfolio/positions")
async def get_portfolio_positions() -> dict[str, object]:
    summary = compute_portfolio()
    return {
        "positions": summary["positions"],
        "source": "dry-run-cache" if summary["mode"] == "dry-run" else "broker",
        "last_sync_at": summary["last_sync_at"],
    }


@router.get("/portfolio/pnl")
async def get_portfolio_pnl(days: int = Query(default=30, ge=1, le=365)) -> dict[str, object]:
    series = portfolio_pnl_series(days=days)
    return {"series": series, "days": days}


@router.post("/portfolio/refresh")
async def refresh_portfolio() -> dict[str, object]:
    summary = save_portfolio_snapshot()
    return {
        "success": True,
        "mode": summary["mode"],
        "cash": summary["cash"],
        "nav": summary["nav"],
        "purchasing_power": summary["purchasing_power"],
        "last_sync_at": summary["last_sync_at"],
    }


@router.post("/portfolio/reconcile")
async def reconcile_portfolio() -> dict[str, object]:
    summary = compute_portfolio()
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
        "matched": len(mismatches) == 0,
        "mismatches": mismatches,
        "snapshot_at": str(latest[3]),
        "checked_at": datetime.now(UTC).isoformat(),
    }
