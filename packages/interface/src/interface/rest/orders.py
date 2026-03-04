from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from interface.observability import get_correlation_id, record_event
from interface.trading_store import (
    compute_portfolio,
    enqueue_dlq,
    get_idempotency_store,
    get_order,
    get_safety_state,
    get_trading_mode,
    list_dlq,
    list_orders,
    log_order_audit,
    market_session_open,
    now_utc,
    recent_rejection_count,
    record_order_rejection,
    reference_prices,
    save_portfolio_snapshot,
    set_order_status,
    set_safety_state,
    try_replay_dlq,
    upsert_order,
)

router = APIRouter(tags=["orders"])


class PlaceOrderRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=10)
    side: Literal["BUY", "SELL"]
    order_type: Literal["LO", "ATO", "ATC", "MP"] = "LO"
    quantity: int = Field(ge=100, le=10_000_000)
    price: Decimal = Field(gt=Decimal("0"))
    idempotency_key: str = Field(min_length=8, max_length=128)
    mode: Literal["dry-run", "live"] | None = None
    confirm_token: str | None = None

    @field_validator("symbol")
    @classmethod
    def _norm_symbol(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if not cleaned.isalnum():
            msg = "Symbol must be alphanumeric."
            raise ValueError(msg)
        return cleaned

    @field_validator("quantity")
    @classmethod
    def _validate_lot(cls, value: int) -> int:
        if value % 100 != 0:
            msg = "Quantity must be a multiple of 100."
            raise ValueError(msg)
        return value


class CancelOrderResponse(BaseModel):
    success: bool
    order_id: str
    status: str


class DLQReplayRequest(BaseModel):
    dlq_id: str | None = None


class KillSwitchRequest(BaseModel):
    active: bool
    reason: str = Field(default="", max_length=300)


def _is_true(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _payload_hash(payload: PlaceOrderRequest, mode: str) -> str:
    price = payload.price.quantize(Decimal("0.000001"))
    canonical = {
        "symbol": payload.symbol,
        "side": payload.side,
        "order_type": payload.order_type,
        "quantity": payload.quantity,
        "price": str(price),
        "mode": mode,
        "idempotency_key": payload.idempotency_key,
    }
    encoded = json.dumps(canonical, ensure_ascii=True, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _as_decimal(value: Any, default: str = "0") -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def _validate_live_guardrails(payload: PlaceOrderRequest, mode: str) -> dict[str, Any]:
    if mode != "live":
        return {}

    kill = get_safety_state("kill_switch", {"active": False})
    if bool(kill.get("active")):
        reason = str(kill.get("reason") or "Kill switch active")
        record_order_rejection(None, f"LIVE_BLOCKED_KILL_SWITCH: {reason}")
        record_event(
            flow="orders",
            level="warn",
            message=f"Live order blocked by kill-switch: {reason}",
            metadata={"symbol": payload.symbol, "side": payload.side},
        )
        raise HTTPException(status_code=423, detail=reason)

    if not market_session_open():
        record_order_rejection(None, "LIVE_BLOCKED_SESSION_CLOSED")
        record_event(
            flow="orders",
            level="warn",
            message="Live order blocked: session closed",
            metadata={"symbol": payload.symbol, "side": payload.side},
        )
        raise HTTPException(status_code=409, detail="Live mode allowed only during market session.")

    cooldown_threshold = int(os.getenv("ORDER_REJECT_COOLDOWN_THRESHOLD", "3"))
    if recent_rejection_count(window_minutes=10) >= cooldown_threshold:
        record_order_rejection(None, "LIVE_BLOCKED_REJECTION_COOLDOWN")
        record_event(
            flow="orders",
            level="warn",
            message="Live order blocked: rejection cooldown active",
            metadata={"symbol": payload.symbol, "side": payload.side},
        )
        raise HTTPException(status_code=429, detail="Cooldown active after repeated rejections.")

    summary = compute_portfolio(mode=mode)
    pnl_total = _as_decimal(summary.get("realized_pnl", 0)) + _as_decimal(summary.get("unrealized_pnl", 0))
    daily_loss = max(Decimal("0"), -pnl_total)
    max_daily_loss = _as_decimal(os.getenv("MAX_DAILY_LOSS", "50000000"))
    if daily_loss > max_daily_loss:
        record_order_rejection(None, "LIVE_BLOCKED_DAILY_LOSS")
        record_event(
            flow="orders",
            level="warn",
            message="Live order blocked: daily loss limit exceeded",
            metadata={"symbol": payload.symbol, "side": payload.side},
        )
        raise HTTPException(status_code=409, detail="Daily loss limit exceeded.")

    notional = payload.price * Decimal(payload.quantity)
    max_notional = _as_decimal(os.getenv("MAX_ORDER_NOTIONAL", "200000000"))
    if notional > max_notional:
        record_order_rejection(None, "LIVE_BLOCKED_MAX_NOTIONAL")
        record_event(
            flow="orders",
            level="warn",
            message="Live order blocked: max notional exceeded",
            metadata={"symbol": payload.symbol, "side": payload.side},
        )
        raise HTTPException(status_code=409, detail=f"Order notional exceeds limit {float(max_notional):,.0f}.")

    buying_power = _as_decimal(summary.get("purchasing_power", 0))
    if payload.side == "BUY" and notional > buying_power:
        record_order_rejection(None, "LIVE_BLOCKED_BUYING_POWER")
        record_event(
            flow="orders",
            level="warn",
            message="Live order blocked: insufficient buying power",
            metadata={"symbol": payload.symbol, "side": payload.side},
        )
        raise HTTPException(status_code=409, detail="Insufficient purchasing power.")

    return {"portfolio": summary, "notional": float(notional)}


def _live_confirm_key(token: str) -> str:
    return f"live_confirm:{token}"


def _issue_live_confirm(payload: PlaceOrderRequest, mode: str) -> dict[str, Any]:
    token = str(uuid.uuid4())
    expires_at = now_utc() + timedelta(minutes=2)
    set_safety_state(
        _live_confirm_key(token),
        {
            "hash": _payload_hash(payload, mode),
            "expires_at": expires_at.isoformat(),
            "created_at": now_utc().isoformat(),
        },
    )
    return {
        "success": False,
        "requires_confirmation": True,
        "confirm_token": token,
        "expires_at": expires_at.isoformat(),
        "message": "Live order requires second-step confirmation.",
    }


def _validate_live_confirm(payload: PlaceOrderRequest, mode: str) -> dict[str, Any] | None:
    if mode != "live":
        return None
    if not payload.confirm_token:
        return _issue_live_confirm(payload, mode)

    state = get_safety_state(_live_confirm_key(payload.confirm_token), {})
    if not state:
        raise HTTPException(status_code=400, detail="Invalid or expired confirm_token.")

    expected_hash = str(state.get("hash", ""))
    if expected_hash != _payload_hash(payload, mode):
        raise HTTPException(status_code=400, detail="confirm_token payload mismatch.")

    expires_raw = str(state.get("expires_at", ""))
    if not expires_raw:
        raise HTTPException(status_code=400, detail="Invalid confirmation state.")

    expires_at = datetime.fromisoformat(expires_raw.replace("Z", "+00:00"))
    if now_utc() > expires_at:
        raise HTTPException(status_code=400, detail="confirm_token expired.")

    set_safety_state(_live_confirm_key(payload.confirm_token), {"consumed_at": now_utc().isoformat(), "used": True})
    return None


def _broker_live_enabled() -> bool:
    return _is_true(os.getenv("ENABLE_LIVE_BROKER", "false"))


@router.post("/orders")
async def place_order(payload: PlaceOrderRequest) -> dict[str, Any]:
    mode = get_trading_mode(payload.mode)
    _validate_live_guardrails(payload, mode)
    confirm = _validate_live_confirm(payload, mode)
    if confirm is not None:
        return confirm

    idempotency = await get_idempotency_store()
    cached = await idempotency.check(payload.idempotency_key)
    if cached is not None:
        return {**cached, "was_duplicate": True}

    order_id = str(uuid.uuid4())
    payload_json = payload.model_dump(mode="json")
    reference, ceiling, floor = reference_prices(payload.symbol, fallback_price=float(payload.price))
    created_at = now_utc()
    risk_summary = {
        "mode": mode,
        "max_order_notional": float(os.getenv("MAX_ORDER_NOTIONAL", "200000000")),
        "max_daily_loss": float(os.getenv("MAX_DAILY_LOSS", "50000000")),
        "session_open": market_session_open(),
    }

    status = "MATCHED" if mode == "dry-run" else "PENDING"
    broker_order_id: str | None = None
    rejection_reason: str | None = None
    dlq_id: str | None = None
    success = True
    error: str | None = None

    if mode == "live":
        if _broker_live_enabled():
            broker_order_id = f"LIVE-{uuid.uuid4().hex[:10].upper()}"
            status = "PENDING"
        else:
            status = "BROKER_REJECTED"
            rejection_reason = "Live broker adapter unavailable"
            success = False
            error = rejection_reason
            dlq_id = enqueue_dlq(order_id, payload_json, rejection_reason)
            record_order_rejection(order_id, rejection_reason)
            record_event(
                flow="orders",
                level="error",
                message=f"Live broker unavailable. Routed to DLQ: {rejection_reason}",
                metadata={"order_id": order_id, "symbol": payload.symbol},
            )

    order = {
        "order_id": order_id,
        "symbol": payload.symbol,
        "side": payload.side,
        "order_type": payload.order_type,
        "quantity": payload.quantity,
        "req_price": payload.price,
        "ceiling_price": ceiling,
        "floor_price": floor,
        "status": status,
        "filled_quantity": payload.quantity if status == "MATCHED" else 0,
        "avg_fill_price": payload.price if status == "MATCHED" else payload.price,
        "broker_order_id": broker_order_id,
        "rejection_reason": rejection_reason,
        "idempotency_key": payload.idempotency_key,
        "mode": mode,
        "risk_summary": risk_summary,
        "created_at": created_at,
        "updated_at": created_at,
    }
    upsert_order(order)
    log_order_audit(order_id, "placed", {"payload": payload_json, "status": status, "mode": mode, "dlq_id": dlq_id})

    if status == "MATCHED":
        save_portfolio_snapshot(mode=mode)

    result = {
        "success": success,
        "order_id": order_id,
        "broker_order_id": broker_order_id,
        "error": error,
        "was_duplicate": False,
        "status": status,
        "mode": mode,
        "dlq_id": dlq_id,
        "correlation_id": get_correlation_id(),
    }
    await idempotency.record(payload.idempotency_key, result)
    return result


@router.post("/orders/{order_id}/cancel", response_model=CancelOrderResponse)
async def cancel_order(order_id: str) -> CancelOrderResponse:
    updated = set_order_status(order_id, "CANCELLED", "Cancelled by user")
    if updated is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    return CancelOrderResponse(success=True, order_id=order_id, status=str(updated["status"]))


@router.get("/orders")
async def get_orders(
    status: str | None = Query(default=None),
    symbol: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
) -> dict[str, Any]:
    rows = list_orders(limit=limit, status=status, symbol=symbol)
    return {"orders": rows, "count": len(rows), "correlation_id": get_correlation_id()}


@router.get("/orders/open")
async def get_open_orders(limit: int = Query(default=200, ge=1, le=2000)) -> dict[str, Any]:
    statuses = {"CREATED", "PENDING", "PARTIAL_FILL"}
    rows = [o for o in list_orders(limit=limit) if str(o.get("status")) in statuses]
    return {"orders": rows, "count": len(rows), "correlation_id": get_correlation_id()}

@router.get("/orders/dlq")
async def get_order_dlq() -> dict[str, Any]:
    rows = list_dlq()
    return {"items": rows, "count": len(rows), "correlation_id": get_correlation_id()}


@router.post("/orders/dlq/replay")
async def replay_order_dlq(payload: DLQReplayRequest) -> dict[str, Any]:
    replayed = try_replay_dlq(payload.dlq_id)
    return {"replayed": replayed, "count": len(replayed), "correlation_id": get_correlation_id()}


@router.get("/orders/{order_id}")
async def get_order_detail(order_id: str) -> dict[str, Any]:
    order = get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    return order


@router.get("/safety/status")
async def get_safety_status() -> dict[str, Any]:
    kill = get_safety_state("kill_switch", {"active": False, "reason": ""})
    return {
        "kill_switch": kill,
        "market_session_open": market_session_open(),
        "recent_rejections_10m": recent_rejection_count(window_minutes=10),
    }


@router.post("/safety/kill-switch")
async def set_kill_switch(payload: KillSwitchRequest) -> dict[str, Any]:
    state = {"active": payload.active, "reason": payload.reason, "updated_at": now_utc().isoformat()}
    set_safety_state("kill_switch", state)
    return {"success": True, "kill_switch": state}
