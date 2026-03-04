from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from interface.app import create_app
import interface.rest.data_loader as data_loader


def _stream_body(response: TestClient) -> str:  # type: ignore[type-arg]
    return "".join(chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk for chunk in response.iter_bytes())


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    if data_loader._conn is not None:
        data_loader._conn.close()
    data_loader._conn = None

    monkeypatch.setenv("DUCKDB_PATH", str(tmp_path / "data-loader.duckdb"))
    monkeypatch.setattr(data_loader, "VN30_SYMBOLS", ["FPT", "VCB", "HPG"])

    async def _fast_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(data_loader.asyncio, "sleep", _fast_sleep)
    app = create_app()
    return TestClient(app)


def test_load_update_cached_and_candles_flow(client: TestClient) -> None:
    before = client.get("/api/cached-data?preset=VN30")
    assert before.status_code == 200
    assert before.json()["symbol_count"] == 0

    with client.stream("GET", "/api/load-data?preset=VN30&years=1") as response:
        assert response.status_code == 200
        body = _stream_body(response)
    assert "event: complete" in body

    cached = client.get("/api/cached-data?preset=VN30")
    assert cached.status_code == 200
    payload = cached.json()
    assert payload["symbol_count"] >= 3
    assert len(payload["ticks"]) >= 3

    candles = client.get("/api/candles/FPT?limit=100")
    assert candles.status_code == 200
    assert candles.json()["count"] > 0

    fresh = client.get("/api/check-updates?preset=VN30")
    assert fresh.status_code == 200
    assert fresh.json()["reason"] in {"fresh", "stale"}

    conn = data_loader._get_conn()
    conn.execute(
        "UPDATE load_metadata SET last_updated = ? WHERE preset = ?",
        [datetime.now(tz=UTC) - timedelta(hours=72), "VN30"],
    )
    stale = client.get("/api/check-updates?preset=VN30")
    assert stale.status_code == 200
    assert stale.json()["needs_update"] is True
    assert stale.json()["reason"] == "stale"

    with client.stream("GET", "/api/update-data?preset=VN30") as update_response:
        assert update_response.status_code == 200
        update_body = _stream_body(update_response)
    assert "event: complete" in update_body


def test_check_updates_no_data_and_screener_history(client: TestClient) -> None:
    no_data = client.get("/api/check-updates?preset=TOP100")
    assert no_data.status_code == 200
    assert no_data.json()["reason"] in {"no_data", "db_error"}

    with client.stream("GET", "/api/run-screener?preset=VN30&mode=INVALID") as response:
        assert response.status_code == 200
        body = _stream_body(response)
    assert "event: pipeline_start" in body
    assert "event: pipeline_complete" in body
    assert '"mode": "dry-run"' in body

    history = client.get("/api/screener/history?limit=5")
    assert history.status_code == 200
    assert history.json()["count"] >= 1
