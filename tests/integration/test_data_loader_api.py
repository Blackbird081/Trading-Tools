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
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATA_PROVIDER_MODE", "mock")
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


def test_screener_pipeline_survives_missing_prompts_dir(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PROMPTS_DIR", str(tmp_path / "missing-prompts"))
    with client.stream("GET", "/api/run-screener?preset=VN30&mode=dry-run") as response:
        assert response.status_code == 200
        body = _stream_body(response)
    assert "event: pipeline_start" in body
    assert "event: pipeline_complete" in body


def test_production_blocks_mock_provider_mode(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATA_PROVIDER_MODE", "mock")

    with client.stream("GET", "/api/load-data?preset=VN30&years=1") as response:
        assert response.status_code == 200
        body = _stream_body(response)
    assert "event: error" in body
    assert "Mock data provider is disabled in production" in body


def test_live_provider_mode_uses_live_contract(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATA_PROVIDER_MODE", "live")

    def _fake_live_data(symbol: str, _start: object, _end: object) -> tuple[dict[str, object], list[dict[str, object]]]:
        tick = {
            "symbol": symbol,
            "price": 100.0,
            "change": 1.0,
            "changePct": 1.0,
            "volume": 1_000_000,
            "high": 101.0,
            "low": 99.0,
            "open": 99.5,
            "ceiling": 107.0,
            "floor": 93.0,
            "reference": 99.0,
            "timestamp": int(datetime.now(tz=UTC).timestamp() * 1000),
        }
        candles = [
            {
                "symbol": symbol,
                "ts": 1_700_000_000,
                "open": 99.0,
                "high": 101.0,
                "low": 98.0,
                "close": 100.0,
                "volume": 500_000,
            }
        ]
        return tick, candles

    def _fake_live_tick(symbol: str, _preset: str) -> dict[str, object]:
        return {
            "symbol": symbol,
            "price": 101.0,
            "change": 2.0,
            "changePct": 2.0,
            "volume": 1_200_000,
            "high": 102.0,
            "low": 99.0,
            "open": 100.0,
            "ceiling": 107.0,
            "floor": 93.0,
            "reference": 99.0,
            "timestamp": int(datetime.now(tz=UTC).timestamp() * 1000),
        }

    monkeypatch.setattr(data_loader, "_load_symbol_live_data", _fake_live_data)
    monkeypatch.setattr(data_loader, "_load_symbol_live_tick", _fake_live_tick)

    with client.stream("GET", "/api/load-data?preset=VN30&years=1") as response:
        assert response.status_code == 200
        body = _stream_body(response)
    assert "event: complete" in body
    assert '"provider_mode": "live"' in body

    with client.stream("GET", "/api/update-data?preset=VN30") as response:
        assert response.status_code == 200
        update_body = _stream_body(response)
    assert "event: complete" in update_body
