from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from interface.app import create_app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DUCKDB_PATH", str(tmp_path / "local-product.duckdb"))
    monkeypatch.setenv("DRYRUN_INITIAL_CASH", "1000000000")
    app = create_app()
    return TestClient(app)


def test_orders_and_portfolio_dry_run_flow(client: TestClient) -> None:
    place = client.post(
        "/api/orders",
        json={
            "symbol": "FPT",
            "side": "BUY",
            "order_type": "LO",
            "quantity": 100,
            "price": 95.5,
            "idempotency_key": "it-dryrun-fpt-buy-01",
            "mode": "dry-run",
        },
    )
    assert place.status_code == 200
    payload = place.json()
    assert payload["success"] is True
    assert payload["status"] == "MATCHED"

    orders = client.get("/api/orders")
    assert orders.status_code == 200
    orders_data = orders.json()
    assert orders_data["count"] >= 1

    portfolio = client.get("/api/portfolio")
    assert portfolio.status_code == 200
    portfolio_data = portfolio.json()
    assert portfolio_data["mode"] in {"dry-run", "live"}
    assert float(portfolio_data["nav"]) > 0

    positions = client.get("/api/portfolio/positions")
    assert positions.status_code == 200
    assert any(p["symbol"] == "FPT" for p in positions.json()["positions"])

    pnl = client.get("/api/portfolio/pnl?days=7")
    assert pnl.status_code == 200
    assert len(pnl.json()["series"]) >= 1

    refresh = client.post("/api/portfolio/refresh")
    assert refresh.status_code == 200
    assert refresh.json()["success"] is True

    reconcile = client.post("/api/portfolio/reconcile")
    assert reconcile.status_code == 200
    assert reconcile.json()["success"] is True


def test_orders_live_confirmation_and_cancel_flow(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_LIVE_BROKER", "true")
    monkeypatch.setattr("interface.rest.orders.market_session_open", lambda: True)

    first = client.post(
        "/api/orders",
        json={
            "symbol": "FPT",
            "side": "BUY",
            "order_type": "LO",
            "quantity": 100,
            "price": 96.1,
            "idempotency_key": "it-live-fpt-buy-01",
            "mode": "live",
        },
    )
    assert first.status_code == 200
    first_payload = first.json()
    assert first_payload["requires_confirmation"] is True
    token = first_payload["confirm_token"]

    second = client.post(
        "/api/orders",
        json={
            "symbol": "FPT",
            "side": "BUY",
            "order_type": "LO",
            "quantity": 100,
            "price": 96.1,
            "idempotency_key": "it-live-fpt-buy-01",
            "mode": "live",
            "confirm_token": token,
        },
    )
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["success"] is True
    assert second_payload["status"] == "PENDING"
    order_id = second_payload["order_id"]

    cancel = client.post(f"/api/orders/{order_id}/cancel")
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "CANCELLED"


def test_screener_stream_returns_pipeline_complete(client: TestClient) -> None:
    with client.stream("GET", "/api/run-screener?preset=VN30&mode=dry-run") as response:
        assert response.status_code == 200
        body = "".join(chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk for chunk in response.iter_bytes())

    assert "event: pipeline_start" in body
    assert "event: pipeline_complete" in body
    lines = [line for line in body.splitlines() if line.startswith("data: ")]
    payloads = [json.loads(line.replace("data: ", "", 1)) for line in lines]
    completes = [p for p in payloads if isinstance(p, dict) and "run_id" in p and "results" in p]
    assert len(completes) >= 1
    assert isinstance(completes[-1]["results"], list)
    final_payload = completes[-1]
    assert "fundamental_coverage" in final_payload
    assert "news_coverage" in final_payload
    if final_payload["results"]:
        first = final_payload["results"][0]
        assert "fundamental_summary" in first
        assert "news_headlines" in first
        assert "data_sources" in first
