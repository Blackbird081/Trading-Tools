from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

logger = logging.getLogger("core.oms")


@dataclass(frozen=True, slots=True)
class PlaceOrderRequest:
    """Incoming order request."""

    symbol: str
    side: str
    order_type: str
    quantity: int
    price: Decimal
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class PlaceOrderResult:
    success: bool
    order_id: str | None
    broker_order_id: str | None
    error: str | None
    was_duplicate: bool


class IdempotencyStore:
    """In-memory idempotency key store with cache."""

    def __init__(self) -> None:
        self._cache: dict[str, PlaceOrderResult] = {}

    def check(self, key: str) -> PlaceOrderResult | None:
        return self._cache.get(key)

    def record(self, key: str, result: PlaceOrderResult) -> None:
        self._cache[key] = result

    def prune_expired(self, max_age_hours: int = 24) -> int:
        """Remove old keys. Returns count pruned."""
        # Simplified: in production, check timestamps
        return 0


async def place_order(
    request: PlaceOrderRequest,
    broker: Any,
    order_repo: Any,
    idempotency_store: IdempotencyStore,
    risk_check_fn: Any = None,
    dry_run: bool = False,
) -> PlaceOrderResult:
    """Place an order with full safety checks.

    Order of operations:
    1. Idempotency check
    2. Risk validation (optional)
    3. Broker submission (or dry-run)
    4. Persistence
    5. Idempotency record
    """
    # Step 1: Idempotency Check
    cached = idempotency_store.check(request.idempotency_key)
    if cached is not None:
        logger.info("Duplicate order detected: %s", request.idempotency_key)
        return PlaceOrderResult(
            success=cached.success,
            order_id=cached.order_id,
            broker_order_id=cached.broker_order_id,
            error=None,
            was_duplicate=True,
        )

    # Step 2: Risk Validation (optional)
    if risk_check_fn is not None:
        risk_result = risk_check_fn(request)
        if not risk_result.get("approved", True):
            result = PlaceOrderResult(
                success=False,
                order_id=None,
                broker_order_id=None,
                error=risk_result.get("reason", "Risk check failed"),
                was_duplicate=False,
            )
            idempotency_store.record(request.idempotency_key, result)
            return result

    # Step 3: Generate order ID
    order_id = str(uuid.uuid4())

    # Step 4: Broker submission
    broker_order_id: str | None = None
    if not dry_run:
        try:
            broker_order_id = await _submit_to_broker(broker, request)
        except Exception as exc:
            result = PlaceOrderResult(
                success=False,
                order_id=order_id,
                broker_order_id=None,
                error=f"Broker error: {type(exc).__name__}: {exc}",
                was_duplicate=False,
            )
            idempotency_store.record(request.idempotency_key, result)
            return result

    # Step 5: Persist
    if order_repo is not None:
        try:
            await _persist_order(order_repo, order_id, request, broker_order_id)
        except Exception:
            logger.exception("Failed to persist order %s", order_id)

    # Step 6: Record idempotency
    result = PlaceOrderResult(
        success=True,
        order_id=order_id,
        broker_order_id=broker_order_id,
        error=None,
        was_duplicate=False,
    )
    idempotency_store.record(request.idempotency_key, result)

    logger.info(
        "Order placed: %s %s %s x%d @ %s (dry_run=%s)",
        order_id,
        request.side,
        request.symbol,
        request.quantity,
        request.price,
        dry_run,
    )
    return result


async def _submit_to_broker(broker: Any, request: PlaceOrderRequest) -> str:
    """Submit order to broker. Returns broker_order_id."""
    if hasattr(broker, "place_order"):
        result: str = await broker.place_order(
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            quantity=request.quantity,
            price=float(request.price),
        )
        return result
    msg = "Broker does not implement place_order"
    raise NotImplementedError(msg)


async def _persist_order(
    repo: Any,
    order_id: str,
    request: PlaceOrderRequest,
    broker_order_id: str | None,
) -> None:
    """Persist order to repository."""
    if hasattr(repo, "save"):
        await repo.save(
            {
                "order_id": order_id,
                "symbol": request.symbol,
                "side": request.side,
                "order_type": request.order_type,
                "quantity": request.quantity,
                "price": str(request.price),
                "broker_order_id": broker_order_id,
                "status": "PENDING" if broker_order_id else "DRY_RUN",
                "idempotency_key": request.idempotency_key,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
