from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from core.use_cases.place_order import (
    IdempotencyStore,
    PlaceOrderRequest,
    place_order,
)


def _make_request(key: str = "test-key-1") -> PlaceOrderRequest:
    return PlaceOrderRequest(
        symbol="FPT",
        side="BUY",
        order_type="LO",
        quantity=1000,
        price=Decimal("98500"),
        idempotency_key=key,
    )


class TestIdempotencyStore:
    def test_new_key_returns_none(self) -> None:
        store = IdempotencyStore()
        assert store.check("new-key") is None

    def test_recorded_key_returns_result(self) -> None:
        from core.use_cases.place_order import PlaceOrderResult

        store = IdempotencyStore()
        result = PlaceOrderResult(
            success=True,
            order_id="ord-1",
            broker_order_id="brk-1",
            error=None,
            was_duplicate=False,
        )
        store.record("key-1", result)
        cached = store.check("key-1")
        assert cached is not None
        assert cached.order_id == "ord-1"


class TestPlaceOrder:
    @pytest.mark.asyncio
    async def test_successful_order(self) -> None:
        broker = AsyncMock()
        broker.place_order = AsyncMock(return_value="broker-123")
        repo = AsyncMock()
        store = IdempotencyStore()

        result = await place_order(
            request=_make_request(),
            broker=broker,
            order_repo=repo,
            idempotency_store=store,
        )
        assert result.success is True
        assert result.was_duplicate is False
        assert result.broker_order_id == "broker-123"

    @pytest.mark.asyncio
    async def test_duplicate_order_detected(self) -> None:
        broker = AsyncMock()
        broker.place_order = AsyncMock(return_value="broker-123")
        repo = AsyncMock()
        store = IdempotencyStore()

        # First call
        result1 = await place_order(
            request=_make_request("dup-key"),
            broker=broker,
            order_repo=repo,
            idempotency_store=store,
        )
        assert result1.was_duplicate is False

        # Second call with same key
        result2 = await place_order(
            request=_make_request("dup-key"),
            broker=broker,
            order_repo=repo,
            idempotency_store=store,
        )
        assert result2.was_duplicate is True
        broker.place_order.assert_called_once()  # Only called once

    @pytest.mark.asyncio
    async def test_dry_run_no_broker_call(self) -> None:
        broker = AsyncMock()
        repo = AsyncMock()
        store = IdempotencyStore()

        result = await place_order(
            request=_make_request("dry-key"),
            broker=broker,
            order_repo=repo,
            idempotency_store=store,
            dry_run=True,
        )
        assert result.success is True
        assert result.broker_order_id is None
        broker.place_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_broker_error_returns_failure(self) -> None:
        broker = AsyncMock()
        broker.place_order = AsyncMock(side_effect=ConnectionError("API down"))
        repo = AsyncMock()
        store = IdempotencyStore()

        result = await place_order(
            request=_make_request("err-key"),
            broker=broker,
            order_repo=repo,
            idempotency_store=store,
        )
        assert result.success is False
        assert "ConnectionError" in (result.error or "")

    @pytest.mark.asyncio
    async def test_risk_check_rejection(self) -> None:
        broker = AsyncMock()
        repo = AsyncMock()
        store = IdempotencyStore()

        def risk_fn(_req: object) -> dict[str, object]:
            return {"approved": False, "reason": "Kill switch active"}

        result = await place_order(
            request=_make_request("risk-key"),
            broker=broker,
            order_repo=repo,
            idempotency_store=store,
            risk_check_fn=risk_fn,
        )
        assert result.success is False
        assert result.error == "Kill switch active"
