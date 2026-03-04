from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from interface.app import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_setup_status_returns_contract(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRADING_MODE", "dry-run")
    monkeypatch.setenv("DUCKDB_PATH", "data/trading.duckdb")
    response = client.get("/api/setup/status")
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] in {"dry-run", "live"}
    assert isinstance(data["checks"], list)
    assert "data_path" in data
    assert "all_ready" in data


def test_setup_validate_returns_checks(client: TestClient, tmp_path: Path) -> None:
    payload = {
        "trading_mode": "dry-run",
        "duckdb_path": str(tmp_path / "setup-test.duckdb"),
        "vnstock_api_key": "abc1234567890",
        "ssi_consumer_id": "consumer-id",
        "ssi_consumer_secret": "consumer-secret",
        "ssi_account_no": "12345678",
        "ssi_private_key_b64": "dGVzdA==",
        "ai_model_path": str(tmp_path / "model"),
    }
    response = client.post("/api/setup/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["checks"], list)
    assert "recommended_env" in data
    assert "valid" in data


def test_setup_init_local_creates_db(client: TestClient, tmp_path: Path) -> None:
    db_path = tmp_path / "runtime" / "local-trading.duckdb"
    response = client.post("/api/setup/init-local", json={"duckdb_path": str(db_path)})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "initialized"
    assert str(db_path) == data["duckdb_path"]
    assert db_path.exists()

