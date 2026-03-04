from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from interface.app import create_app
import interface.trading_store as trading_store


def _reset_trading_store() -> None:
    if trading_store._CONN is not None:
        trading_store._CONN.close()
    trading_store._CONN = None
    trading_store._IDEMPOTENCY = None


def _build_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    app_env: str = "development",
    auth_required: str = "false",
    auth_token: str | None = "test-auth-token",
    rpm: int = 240,
    order_rpm: int = 60,
) -> TestClient:
    _reset_trading_store()
    monkeypatch.setenv("DUCKDB_PATH", str(tmp_path / "runtime-security.duckdb"))
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv("API_AUTH_REQUIRED", auth_required)
    monkeypatch.setenv("RATE_LIMIT_REQUESTS_PER_MINUTE", str(rpm))
    monkeypatch.setenv("RATE_LIMIT_ORDER_REQUESTS_PER_MINUTE", str(order_rpm))
    if auth_token is None:
        monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
    else:
        monkeypatch.setenv("API_AUTH_TOKEN", auth_token)
    return TestClient(create_app())


def _dry_order_payload(idempotency_key: str) -> dict[str, object]:
    return {
        "symbol": "FPT",
        "side": "BUY",
        "order_type": "LO",
        "quantity": 100,
        "price": 95.0,
        "idempotency_key": idempotency_key,
        "mode": "dry-run",
    }


def test_sensitive_endpoints_require_auth_in_protected_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _build_client(
        tmp_path,
        monkeypatch,
        app_env="production",
        auth_required="true",
        auth_token="super-secret",
    )

    unauth_setup = client.get("/api/setup/status")
    assert unauth_setup.status_code == 401

    bad_token_safety = client.get("/api/safety/status", headers={"X-API-Key": "wrong-token"})
    assert bad_token_safety.status_code == 401

    ok_setup = client.get("/api/setup/status", headers={"Authorization": "Bearer super-secret"})
    assert ok_setup.status_code == 200

    ok_order = client.post(
        "/api/orders",
        json=_dry_order_payload("it-auth-required-01"),
        headers={"X-API-Key": "super-secret"},
    )
    assert ok_order.status_code == 200


def test_protected_mode_without_token_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _build_client(
        tmp_path,
        monkeypatch,
        app_env="production",
        auth_required="true",
        auth_token=None,
    )
    response = client.get("/api/setup/status")
    assert response.status_code == 503
    assert "API_AUTH_TOKEN" in response.json()["detail"]


def test_health_endpoint_not_blocked_by_auth_middleware(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _build_client(
        tmp_path,
        monkeypatch,
        app_env="production",
        auth_required="true",
        auth_token="super-secret",
    )
    health = client.get("/api/health")
    assert health.status_code == 200


def test_order_rate_limit_throttles_when_exceeded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _build_client(
        tmp_path,
        monkeypatch,
        app_env="development",
        auth_required="false",
        rpm=200,
        order_rpm=1,
    )

    first = client.post("/api/orders", json=_dry_order_payload("it-rate-limit-01"))
    assert first.status_code == 200

    second = client.post("/api/orders", json=_dry_order_payload("it-rate-limit-02"))
    assert second.status_code == 429
    assert second.json()["error"] == "Too Many Requests"
