from __future__ import annotations

import logging

from core.entities.order import Order
from core.value_objects import Symbol

logger = logging.getLogger("ssi.broker")


class SSIBrokerClient:
    """SSI BrokerPort implementation — stub for Phase 5.

    Will implement place_order, cancel_order, get_order_status.
    """

    def __init__(self, auth_client: object) -> None:
        self._auth = auth_client

    async def place_order(self, order: Order) -> Order:
        """Submit order to SSI. Stub — raises NotImplementedError."""
        msg = "SSI broker integration not yet implemented (Phase 5)"
        raise NotImplementedError(msg)

    async def cancel_order(self, order_id: str) -> Order:
        msg = "SSI broker integration not yet implemented (Phase 5)"
        raise NotImplementedError(msg)

    async def get_order_status(self, order_id: str) -> Order:
        msg = "SSI broker integration not yet implemented (Phase 5)"
        raise NotImplementedError(msg)

    async def get_open_orders(self, symbol: Symbol | None = None) -> list[Order]:
        msg = "SSI broker integration not yet implemented (Phase 5)"
        raise NotImplementedError(msg)
