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


def test_order_request_validators_and_not_found_paths(client: TestClient) -> None:
    bad_symbol = client.post(
        "/api/orders",
        json={
            "symbol": "FPT@",
            "side": "BUY",
            "order_type": "LO",
            "quantity": 100,
            "price": 90.0,
            "idempotency_key": "it-order-validator-01",
            "mode": "dry-run",
        },
    )
    assert bad_symbol.status_code == 422

    bad_lot = client.post(
        "/api/orders",
        json={
            "symbol": "FPT",
            "side": "BUY",
            "order_type": "LO",
            "quantity": 150,
            "price": 90.0,
            "idempotency_key": "it-order-validator-02",
            "mode": "dry-run",
        },
    )
    assert bad_lot.status_code == 422

    cancel_missing = client.post("/api/orders/not-found/cancel")
    assert cancel_missing.status_code == 404

    detail_missing = client.get("/api/orders/not-found")
    assert detail_missing.status_code == 404


def test_live_session_closed_and_buying_power_blocks(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("interface.rest.orders.market_session_open", lambda: False)
    session_closed = client.post("/api/orders", json=_live_payload("it-live-session-closed-01"))
    assert session_closed.status_code == 409
    assert "market session" in session_closed.json()["detail"]

    monkeypatch.setattr("interface.rest.orders.market_session_open", lambda: True)
    monkeypatch.setattr(
        "interface.rest.orders.compute_portfolio",
        lambda mode=None: {
            "mode": "live",
            "realized_pnl": 0,
            "unrealized_pnl": 0,
            "purchasing_power": 1_000,
        },
    )
    buying_power = client.post("/api/orders", json=_live_payload("it-live-buying-power-01"))
    assert buying_power.status_code == 409
    assert "Insufficient purchasing power" in buying_power.json()["detail"]


def test_live_confirm_token_error_paths(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    first = client.post("/api/orders", json=_live_payload("it-live-confirm-error-01"))
    assert first.status_code == 200
    confirm_token = first.json()["confirm_token"]

    invalid = client.post("/api/orders", json=_live_payload("it-live-confirm-error-02", confirm_token="invalid-token"))
    assert invalid.status_code == 400

    mismatch_payload = _live_payload("it-live-confirm-error-01", confirm_token=confirm_token)
    mismatch_payload["quantity"] = 200
    mismatch = client.post("/api/orders", json=mismatch_payload)
    assert mismatch.status_code == 400
    assert "payload mismatch" in mismatch.json()["detail"]

    expired_payload = _live_payload("it-live-confirm-error-03", confirm_token="expired-token")
    set_safety_state(
        "live_confirm:expired-token",
        {
            "hash": "abc",
            "expires_at": "2000-01-01T00:00:00+00:00",
        },
    )
    monkeypatch.setattr("interface.rest.orders._payload_hash", lambda payload, mode: "abc")
    expired = client.post("/api/orders", json=expired_payload)
    assert expired.status_code == 400
    assert "expired" in expired.json()["detail"]


def test_idempotency_duplicate_open_orders_replay_and_safety_status(client: TestClient) -> None:
    create = client.post(
        "/api/orders",
        json={
            "symbol": "FPT",
            "side": "BUY",
            "order_type": "LO",
            "quantity": 100,
            "price": 91.0,
            "idempotency_key": "it-dry-idempotent-01",
            "mode": "dry-run",
        },
    )
    assert create.status_code == 200
    order_id = create.json()["order_id"]

    duplicate = client.post(
        "/api/orders",
        json={
            "symbol": "FPT",
            "side": "BUY",
            "order_type": "LO",
            "quantity": 100,
            "price": 91.0,
            "idempotency_key": "it-dry-idempotent-01",
            "mode": "dry-run",
        },
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["was_duplicate"] is True

    opened = client.get("/api/orders/open")
    assert opened.status_code == 200
    assert "orders" in opened.json()

    detail = client.get(f"/api/orders/{order_id}")
    assert detail.status_code == 200
    assert detail.json()["order_id"] == order_id

    replay = client.post("/api/orders/dlq/replay", json={})
    assert replay.status_code == 200
    assert "count" in replay.json()

    safety = client.get("/api/safety/status")
    assert safety.status_code == 200
    assert "kill_switch" in safety.json()
