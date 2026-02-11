from __future__ import annotations

import logging

from core.entities.order import Order
from core.value_objects import Symbol

logger = logging.getLogger("dnse.broker")


class DNSEBrokerClient:
    """DNSE BrokerPort implementation — stub for Phase 5."""

    async def place_order(self, order: Order) -> Order:
        msg = "DNSE broker integration not yet implemented (Phase 5)"
        raise NotImplementedError(msg)

    async def cancel_order(self, order_id: str) -> Order:
        msg = "DNSE broker integration not yet implemented (Phase 5)"
        raise NotImplementedError(msg)

    async def get_order_status(self, order_id: str) -> Order:
        msg = "DNSE broker integration not yet implemented (Phase 5)"
        raise NotImplementedError(msg)

    async def get_open_orders(self, symbol: Symbol | None = None) -> list[Order]:
        msg = "DNSE broker integration not yet implemented (Phase 5)"
        raise NotImplementedError(msg)
