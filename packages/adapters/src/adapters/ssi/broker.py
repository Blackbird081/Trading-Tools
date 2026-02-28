"""SSI Broker Client — implements core.ports.broker.BrokerPort.

★ Uses SSI FastConnect Trading API v2.
★ Circuit breaker + retry for resilience.
★ All prices sent as strings to preserve Decimal precision.
"""
from __future__ import annotations
import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
import httpx
from adapters.circuit_breaker import CircuitBreaker
from adapters.retry import RetryConfig, retry_async
from core.entities.order import Order, OrderSide, OrderStatus, OrderType
from core.value_objects import Price, Quantity, Symbol

logger = logging.getLogger("ssi.broker")

SSI_TRADING_BASE = "https://fc-tradeapi.ssi.com.vn/api/v2/Trading"
SSI_ORDER_URL = f"{SSI_TRADING_BASE}/NewOrder"
SSI_CANCEL_URL = f"{SSI_TRADING_BASE}/CancelOrder"
SSI_ORDER_STATUS_URL = f"{SSI_TRADING_BASE}/OrderStatus"
SSI_OPEN_ORDERS_URL = f"{SSI_TRADING_BASE}/OrderBook"

_SSI_STATUS_MAP: dict[str, OrderStatus] = {
    "New": OrderStatus.PENDING, "Pending": OrderStatus.PENDING,
    "PartiallyFilled": OrderStatus.PARTIAL_FILL, "Filled": OrderStatus.MATCHED,
    "Cancelled": OrderStatus.CANCELLED, "Rejected": OrderStatus.BROKER_REJECTED,
    "Expired": OrderStatus.CANCELLED,
}

_RETRY_CONFIG = RetryConfig(
    max_retries=3, base_delay=1.0, max_delay=10.0, jitter=True,
    retryable_exceptions=(ConnectionError, TimeoutError, httpx.TransportError),
)


class SSIBrokerError(Exception):
    """Raised when SSI broker API returns an error."""


class SSIBrokerClient:
    """SSI BrokerPort implementation — FastConnect Trading API v2."""

    def __init__(self, auth_client: Any, account_no: str, http_client: httpx.AsyncClient | None = None) -> None:
        self._auth = auth_client
        self._account_no = account_no
        self._http = http_client or httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0), verify=True)
        self._circuit = CircuitBreaker(name="ssi_broker", failure_threshold=5, recovery_timeout=30.0)

    async def place_order(self, order: Order) -> Order:
        return await self._circuit.call(self._place_order_impl, order)

    async def _place_order_impl(self, order: Order) -> Order:
        token = await self._auth.get_access_token()
        payload = {
            "account": self._account_no, "requestID": order.idempotency_key,
            "instrumentID": str(order.symbol), "market": "VN",
            "buySell": "B" if order.side == OrderSide.BUY else "S",
            "orderType": order.order_type.value,
            "price": str(order.price),  # ★ String, not float
            "quantity": order.quantity,
        }
        async def _call() -> dict[str, Any]:
            r = await self._http.post(SSI_ORDER_URL, json=payload, headers={"Authorization": f"Bearer {token}"})
            r.raise_for_status()
            return r.json()  # type: ignore[no-any-return]
        data = await retry_async(_call, config=_RETRY_CONFIG, operation_name="ssi.place_order")
        if data.get("status") != 200:
            raise SSIBrokerError(f"SSI order rejected: {data.get('message', 'Unknown')}")
        broker_order_id = str(data["data"]["orderID"])
        return order.transition_to(OrderStatus.PENDING, broker_order_id=broker_order_id, updated_at=datetime.now(UTC))

    async def cancel_order(self, order_id: str) -> Order:
        return await self._circuit.call(self._cancel_order_impl, order_id)

    async def _cancel_order_impl(self, order_id: str) -> Order:
        """Cancel an order and return its updated status from SSI.

        ★ Fix: fetch order status AFTER cancel to get real Order data (not stub).
        """
        token = await self._auth.get_access_token()

        async def _call() -> dict[str, Any]:
            r = await self._http.post(
                SSI_CANCEL_URL,
                json={
                    "account": self._account_no,
                    "orderID": order_id,
                    "requestID": f"cancel-{order_id}",
                    "market": "VN",
                    "instrumentID": "",
                    "buySell": "B",
                    "orderType": "LO",
                    "price": "0",
                    "quantity": 0,
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            r.raise_for_status()
            return r.json()  # type: ignore[no-any-return]

        await retry_async(_call, config=_RETRY_CONFIG, operation_name="ssi.cancel_order")

        # ★ Fix: fetch real order status after cancel (not a stub with Symbol(""))
        try:
            return await self._get_order_status_impl(order_id)
        except Exception:
            # Fallback: return minimal cancelled order if status fetch fails
            logger.warning("Could not fetch order status after cancel for %s", order_id)
            now = datetime.now(UTC)
            return Order(
                order_id=order_id,
                symbol=Symbol("UNKNOWN"),  # ★ Use "UNKNOWN" not "" to avoid empty symbol issues
                side=OrderSide.BUY,
                order_type=OrderType.LO,
                quantity=Quantity(0),
                price=Price(Decimal("0")),
                ceiling_price=Price(Decimal("0")),
                floor_price=Price(Decimal("0")),
                status=OrderStatus.CANCELLED,
                filled_quantity=Quantity(0),
                avg_fill_price=Price(Decimal("0")),
                broker_order_id=order_id,
                rejection_reason=None,
                idempotency_key=f"cancel-{order_id}",
                created_at=now,
                updated_at=now,
            )

    async def get_order_status(self, order_id: str) -> Order:
        return await self._circuit.call(self._get_order_status_impl, order_id)

    async def _get_order_status_impl(self, order_id: str) -> Order:
        token = await self._auth.get_access_token()
        async def _call() -> dict[str, Any]:
            r = await self._http.get(SSI_ORDER_STATUS_URL, params={"account": self._account_no, "orderID": order_id}, headers={"Authorization": f"Bearer {token}"})
            r.raise_for_status()
            return r.json()  # type: ignore[no-any-return]
        data = await retry_async(_call, config=_RETRY_CONFIG, operation_name="ssi.get_order_status")
        if data.get("status") != 200:
            raise SSIBrokerError(f"SSI order status failed: {data.get('message', 'Unknown')}")
        return self._parse_order(data["data"])

    async def get_open_orders(self, symbol: Symbol | None = None) -> list[Order]:
        return await self._circuit.call(self._get_open_orders_impl, symbol)

    async def _get_open_orders_impl(self, symbol: Symbol | None) -> list[Order]:
        token = await self._auth.get_access_token()
        params: dict[str, str] = {"account": self._account_no}
        if symbol:
            params["instrumentID"] = str(symbol)
        async def _call() -> dict[str, Any]:
            r = await self._http.get(SSI_OPEN_ORDERS_URL, params=params, headers={"Authorization": f"Bearer {token}"})
            r.raise_for_status()
            return r.json()  # type: ignore[no-any-return]
        data = await retry_async(_call, config=_RETRY_CONFIG, operation_name="ssi.get_open_orders")
        if data.get("status") != 200:
            return []
        return [self._parse_order(o) for o in (data.get("data", []) or [])]

    def _parse_order(self, data: dict[str, Any]) -> Order:
        now = datetime.now(UTC)
        status = _SSI_STATUS_MAP.get(str(data.get("orderStatus", "Pending")), OrderStatus.PENDING)
        side = OrderSide.BUY if str(data.get("buySell", "B")) == "B" else OrderSide.SELL

        # ★ Fix: handle invalid OrderType gracefully (SSI may return unknown types)
        raw_order_type = str(data.get("orderType", "LO"))
        try:
            order_type = OrderType(raw_order_type)
        except ValueError:
            logger.warning("Unknown SSI order type '%s', defaulting to LO", raw_order_type)
            order_type = OrderType.LO

        return Order(
            order_id=str(data.get("requestID", "")),
            symbol=Symbol(str(data.get("instrumentID", ""))),
            side=side,
            order_type=order_type,  # ★ Fixed: no longer raises ValueError
            quantity=Quantity(int(data.get("orderQty", 0))),
            price=Price(Decimal(str(data.get("price", "0")))),
            ceiling_price=Price(Decimal(str(data.get("ceilingPrice", "0")))),
            floor_price=Price(Decimal(str(data.get("floorPrice", "0")))),
            status=status,
            filled_quantity=Quantity(int(data.get("filledQty", 0))),
            avg_fill_price=Price(Decimal(str(data.get("avgPrice", "0")))),
            broker_order_id=str(data.get("orderID", "")),
            rejection_reason=data.get("rejectReason"),
            idempotency_key=str(data.get("requestID", "")),
            created_at=now,
            updated_at=now,
        )

    async def close(self) -> None:
        await self._http.aclose()
