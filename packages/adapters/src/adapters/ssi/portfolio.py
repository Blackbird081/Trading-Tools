from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx

from adapters.retry import RetryConfig, retry_async

from core.entities.portfolio import CashBalance, PortfolioState, Position
from core.value_objects import Price, Quantity, Symbol

logger = logging.getLogger("ssi.portfolio")

SSI_TRADING_BASE = "https://fc-tradeapi.ssi.com.vn/api/v2/Trading"
SSI_STOCK_POSITION_URL = f"{SSI_TRADING_BASE}/stockPosition"
SSI_CASH_BALANCE_URL = f"{SSI_TRADING_BASE}/cashBalance"

_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    base_delay=1.0,
    max_delay=8.0,
    jitter=True,
    retryable_exceptions=(ConnectionError, TimeoutError, httpx.TransportError),
)


class SSIPortfolioClient:
    """SSI portfolio sync — stockPosition + cash balance."""

    def __init__(self, auth_client: object, http_client: httpx.AsyncClient | None = None) -> None:
        self._auth = auth_client
        self._http = http_client or httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=5.0), verify=True)

    @staticmethod
    def _as_decimal(data: dict[str, Any], *keys: str, default: str = "0") -> Decimal:
        for key in keys:
            if key in data and data[key] is not None:
                try:
                    return Decimal(str(data[key]))
                except Exception:
                    continue
        return Decimal(default)

    @staticmethod
    def _as_int(data: dict[str, Any], *keys: str, default: int = 0) -> int:
        for key in keys:
            if key in data and data[key] is not None:
                try:
                    return int(Decimal(str(data[key])))
                except Exception:
                    continue
        return default

    @staticmethod
    def _normalize_rows(payload: dict[str, Any], *candidate_keys: str) -> list[dict[str, Any]]:
        data = payload.get("data", payload)
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]
        if isinstance(data, dict):
            for key in candidate_keys:
                value = data.get(key)
                if isinstance(value, list):
                    return [row for row in value if isinstance(row, dict)]
        return []

    async def _request_json(self, url: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        token = await self._auth.get_access_token()

        async def _call() -> dict[str, Any]:
            response = await self._http.get(
                url,
                params=params or {},
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()  # type: ignore[assignment]
            return payload

        payload = await retry_async(
            _call,
            config=_RETRY_CONFIG,
            operation_name=f"ssi.portfolio:{url.rsplit('/', 1)[-1]}",
        )
        status = int(payload.get("status", 0) or 0)
        if status and status != 200:
            msg = str(payload.get("message", "Unknown SSI portfolio error"))
            raise RuntimeError(msg)
        return payload

    async def _fetch_positions(self) -> tuple[Position, ...]:
        payload = await self._request_json(SSI_STOCK_POSITION_URL)
        rows = self._normalize_rows(payload, "items", "positions", "stockPosition")
        positions: list[Position] = []
        for row in rows:
            symbol_raw = str(row.get("symbol") or row.get("instrumentID") or "").strip().upper()
            if not symbol_raw:
                continue
            on_hand = self._as_int(row, "onHand", "quantity", "qty")
            sellable = self._as_int(row, "sellableQty", "sellable_qty", default=on_hand)
            receiving_t1 = self._as_int(row, "receivingT1", "receiving_t1")
            receiving_t2 = self._as_int(row, "receivingT2", "receiving_t2")
            avg_price = self._as_decimal(row, "avgPrice", "avg_price")
            market_price = self._as_decimal(row, "marketPrice", "market_price", "lastPrice")
            positions.append(
                Position(
                    symbol=Symbol(symbol_raw),
                    quantity=Quantity(max(on_hand, 0)),
                    sellable_qty=Quantity(max(min(sellable, on_hand), 0)),
                    receiving_t1=Quantity(max(receiving_t1, 0)),
                    receiving_t2=Quantity(max(receiving_t2, 0)),
                    avg_price=Price(avg_price),
                    market_price=Price(market_price),
                ),
            )
        return tuple(positions)

    async def _fetch_cash(self) -> CashBalance:
        payload = await self._request_json(SSI_CASH_BALANCE_URL)
        data = payload.get("data", payload)
        row = data if isinstance(data, dict) else {}
        cash_bal = self._as_decimal(row, "cashBal", "cash_balance", "cash")
        buying_power = self._as_decimal(row, "purchasingPower", "purchasing_power", "buyingPower", "buying_power")
        pending = self._as_decimal(row, "pendingSettlement", "pending_settlement")
        return CashBalance(
            cash_bal=cash_bal,
            purchasing_power=buying_power if buying_power > 0 else cash_bal,
            pending_settlement=pending,
        )

    async def get_portfolio(self) -> PortfolioState:
        """Fetch current portfolio state from SSI API."""
        logger.info("Fetching portfolio from SSI")
        positions, cash = await self._fetch_positions(), await self._fetch_cash()
        return PortfolioState(
            positions=positions,
            cash=cash,
            synced_at=datetime.now(UTC),
        )

    async def close(self) -> None:
        await self._http.aclose()
