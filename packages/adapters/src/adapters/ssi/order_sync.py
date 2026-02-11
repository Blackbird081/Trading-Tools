from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger("oms.sync")

# SSI status → local status mapping
SSI_STATUS_MAP: dict[str, str] = {
    "New": "PENDING",
    "Pending": "PENDING",
    "PartiallyFilled": "PARTIAL",
    "Filled": "MATCHED",
    "Cancelled": "CANCELLED",
    "Rejected": "BROKER_REJECTED",
    "Expired": "CANCELLED",
}


class OrderStatusSynchronizer:
    """Periodically syncs order status from broker to local DB.

    Broker is source of truth. Local status converges toward broker status.
    """

    def __init__(
        self,
        broker_client: Any,
        order_repo: Any,
        poll_interval: float = 2.0,
    ) -> None:
        self._broker = broker_client
        self._repo = order_repo
        self._poll_interval = poll_interval
        self._running = False

    async def start(self) -> None:
        """Start the sync loop."""
        self._running = True
        logger.info("Order sync started (interval=%.1fs)", self._poll_interval)
        while self._running:
            try:
                await self._sync_cycle()
            except Exception:
                logger.exception("Order sync cycle failed")
            await asyncio.sleep(self._poll_interval)

    async def stop(self) -> None:
        self._running = False
        logger.info("Order sync stopped")

    async def _sync_cycle(self) -> None:
        """One synchronization cycle."""
        open_orders = await self._get_open_orders()
        if not open_orders:
            return

        broker_ids: list[str] = [
            str(o.get("broker_order_id") or o.get("broker_id"))
            for o in open_orders
            if o.get("broker_order_id") or o.get("broker_id")
        ]
        if not broker_ids:
            return

        broker_statuses = await self._fetch_broker_statuses(broker_ids)

        for order in open_orders:
            bid = order.get("broker_order_id") or order.get("broker_id")
            if bid is None or bid not in broker_statuses:
                continue

            broker_data = broker_statuses[bid]
            new_status = self.reconcile_status(broker_data)
            old_status = order.get("status", "")

            if new_status and new_status != old_status:
                await self._update_order(order, new_status, broker_data)
                logger.info(
                    "Order %s: %s -> %s",
                    order.get("order_id", "?"),
                    old_status,
                    new_status,
                )

    async def _get_open_orders(self) -> list[dict[str, Any]]:
        try:
            if hasattr(self._repo, "get_open_orders"):
                result: list[dict[str, Any]] = await self._repo.get_open_orders()
                return result
        except Exception:
            logger.exception("Failed to fetch open orders")
        return []

    async def _fetch_broker_statuses(
        self,
        broker_ids: list[str],
    ) -> dict[str, dict[str, Any]]:
        try:
            if hasattr(self._broker, "get_order_statuses"):
                result: dict[str, dict[str, Any]] = await self._broker.get_order_statuses(
                    broker_ids
                )
                return result
        except Exception:
            logger.exception("Failed to fetch broker statuses")
        return {}

    async def _update_order(
        self,
        order: dict[str, Any],
        new_status: str,
        broker_data: dict[str, Any],
    ) -> None:
        try:
            if hasattr(self._repo, "update_status"):
                await self._repo.update_status(
                    order.get("order_id", ""),
                    new_status,
                    broker_data,
                )
        except Exception:
            logger.exception("Failed to update order status")

    @staticmethod
    def reconcile_status(broker_data: dict[str, Any]) -> str | None:
        """Map broker status to local status."""
        ssi_status = broker_data.get("status", "")
        return SSI_STATUS_MAP.get(ssi_status)
