from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from interface.app import create_app
import interface.trading_store as trading_store
from interface.trading_store import record_order_rejection, set_safety_state


def _live_payload(idempotency_key: str, confirm_token: str | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "symbol": "FPT",
        "side": "BUY",
        "order_type": "LO",
        "quantity": 100,
        "price": 95.0,
        "idempotency_key": idempotency_key,
        "mode": "live",
    }
    if confirm_token is not None:
        payload["confirm_token"] = confirm_token
    return payload


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    if trading_store._CONN is not None:
        trading_store._CONN.close()
    trading_store._CONN = None
    trading_store._IDEMPOTENCY = None
    monkeypatch.setenv("DUCKDB_PATH", str(tmp_path / "safety-controls.duckdb"))
    monkeypatch.setenv("DRYRUN_INITIAL_CASH", "1000000000")
    monkeypatch.setenv("ENABLE_LIVE_BROKER", "false")
    monkeypatch.setattr("interface.rest.orders.market_session_open", lambda: True)
    set_safety_state("kill_switch", {"active": False, "reason": ""})
    return TestClient(create_app())


def test_kill_switch_blocks_live_orders(client: TestClient) -> None:
    enabled = client.post("/api/safety/kill-switch", json={"active": True, "reason": "manual emergency stop"})
    assert enabled.status_code == 200

    response = client.post("/api/orders", json=_live_payload("it-live-kill-switch-01"))
    assert response.status_code == 423
    assert "manual emergency stop" in response.json()["detail"]


def test_live_order_falls_back_to_dlq_when_broker_disabled(client: TestClient) -> None:
    first = client.post("/api/orders", json=_live_payload("it-live-dlq-01"))
    assert first.status_code == 200
    token = first.json()["confirm_token"]

    second = client.post("/api/orders", json=_live_payload("it-live-dlq-01", confirm_token=token))
    assert second.status_code == 200
    payload = second.json()
    assert payload["success"] is False
    assert payload["status"] == "BROKER_REJECTED"
    assert payload["dlq_id"] is not None

    dlq = client.get("/api/orders/dlq")
    assert dlq.status_code == 200
    assert dlq.json()["count"] >= 1


def test_rejection_cooldown_blocks_live_orders(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORDER_REJECT_COOLDOWN_THRESHOLD", "2")
    record_order_rejection(None, "manual-rejection-1")
    record_order_rejection(None, "manual-rejection-2")

    response = client.post("/api/orders", json=_live_payload("it-live-cooldown-01"))
    assert response.status_code == 429
    assert "Cooldown active" in response.json()["detail"]


def test_daily_loss_limit_blocks_live_orders(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_DAILY_LOSS", "1000000")
    monkeypatch.setattr(
        "interface.rest.orders.compute_portfolio",
        lambda mode=None: {
            "mode": mode or "live",
            "realized_pnl": -2_000_000,
            "unrealized_pnl": 0,
            "purchasing_power": 1_000_000_000,
        },
    )

    response = client.post("/api/orders", json=_live_payload("it-live-daily-loss-01"))
    assert response.status_code == 409
    assert "Daily loss limit exceeded" in response.json()["detail"]


def test_max_notional_blocks_live_orders(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_ORDER_NOTIONAL", "1000000")
    oversized = _live_payload("it-live-notional-01")
    oversized["quantity"] = 20_000
    oversized["price"] = 120.0

    response = client.post("/api/orders", json=oversized)
    assert response.status_code == 409
    assert "Order notional exceeds limit" in response.json()["detail"]
