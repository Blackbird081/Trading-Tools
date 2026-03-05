from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from interface.app import create_app
from interface.rest import data_loader


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_correlation_id_propagates_to_response_and_payload(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(data_loader, "_get_conn", lambda: (_ for _ in ()).throw(RuntimeError("db unavailable")))
    response = client.get("/api/cached-data?preset=VN30", headers={"X-Correlation-ID": "cid-test-001"})
    assert response.status_code == 200
    assert response.headers.get("X-Correlation-ID") == "cid-test-001"
    payload = response.json()
    assert payload["correlation_id"] == "cid-test-001"
    assert payload["error"] == "db unavailable"


def test_observability_events_includes_failed_flow(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(data_loader, "_get_conn", lambda: (_ for _ in ()).throw(RuntimeError("db unavailable")))
    client.get("/api/cached-data?preset=TOP100", headers={"X-Correlation-ID": "cid-obs-002"})
    response = client.get("/api/observability/events?flow=load&limit=20")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] >= 1
    assert any(event.get("flow") == "load" for event in body["events"])
    assert any(event.get("correlation_id") == "cid-obs-002" for event in body["events"])


def test_websocket_events_include_correlation_id(client: TestClient) -> None:
    with client.websocket_connect("/ws/market", headers={"X-Correlation-ID": "cid-ws-003"}) as ws:
        ws.send_text('{"type":"ping"}')

    response = client.get("/api/observability/events?flow=ws&limit=20")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] >= 1
    assert any(event.get("correlation_id") == "cid-ws-003" for event in body["events"])
