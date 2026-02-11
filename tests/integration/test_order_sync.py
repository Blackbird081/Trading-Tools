from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from adapters.ssi.order_sync import SSI_STATUS_MAP, OrderStatusSynchronizer


class TestSSIStatusMapping:
    def test_filled_maps_to_matched(self) -> None:
        assert SSI_STATUS_MAP["Filled"] == "MATCHED"

    def test_rejected_maps_to_broker_rejected(self) -> None:
        assert SSI_STATUS_MAP["Rejected"] == "BROKER_REJECTED"

    def test_new_maps_to_pending(self) -> None:
        assert SSI_STATUS_MAP["New"] == "PENDING"

    def test_partially_filled_maps_to_partial(self) -> None:
        assert SSI_STATUS_MAP["PartiallyFilled"] == "PARTIAL"

    def test_cancelled_maps_to_cancelled(self) -> None:
        assert SSI_STATUS_MAP["Cancelled"] == "CANCELLED"


class TestReconcileStatus:
    def test_reconcile_filled(self) -> None:
        result = OrderStatusSynchronizer.reconcile_status({"status": "Filled"})
        assert result == "MATCHED"

    def test_reconcile_unknown_returns_none(self) -> None:
        result = OrderStatusSynchronizer.reconcile_status({"status": "UnknownStatus"})
        assert result is None


class TestOrderSyncCycle:
    @pytest.mark.asyncio
    async def test_sync_updates_order_status(self) -> None:
        broker = AsyncMock()
        broker.get_order_statuses = AsyncMock(
            return_value={
                "brk-1": {"status": "Filled", "filled_qty": 1000},
            }
        )

        repo = AsyncMock()
        repo.get_open_orders = AsyncMock(
            return_value=[
                {
                    "order_id": "ord-1",
                    "broker_order_id": "brk-1",
                    "status": "PENDING",
                }
            ]
        )
        repo.update_status = AsyncMock()

        sync = OrderStatusSynchronizer(
            broker_client=broker,
            order_repo=repo,
            poll_interval=0.1,
        )
        await sync._sync_cycle()

        repo.update_status.assert_called_once_with(
            "ord-1",
            "MATCHED",
            {"status": "Filled", "filled_qty": 1000},
        )

    @pytest.mark.asyncio
    async def test_sync_no_open_orders_skips(self) -> None:
        broker = AsyncMock()
        repo = AsyncMock()
        repo.get_open_orders = AsyncMock(return_value=[])

        sync = OrderStatusSynchronizer(
            broker_client=broker,
            order_repo=repo,
        )
        await sync._sync_cycle()

        broker.get_order_statuses.assert_not_called()
