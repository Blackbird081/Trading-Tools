from __future__ import annotations

import sys
import types
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
    names = {item.get("name") for item in data["checks"]}
    assert "cache_integrity" in names
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
        "ai_provider": "deterministic",
        "ai_fallback_order": "anthropic,gemini,deterministic",
        "ai_timeout_seconds": 15,
        "ai_budget_usd_per_run": 0.3,
        "ai_max_remote_calls": 20,
        "openai_api_key": "",
        "openai_model": "gpt-5-mini",
        "ai_model_path": str(tmp_path / "model"),
    }
    response = client.post("/api/setup/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["checks"], list)
    assert "recommended_env" in data
    assert "valid" in data
    assert "AGENT_AI_PROVIDER" in data["recommended_env"]
    assert "ANTHROPIC_MODEL" in data["recommended_env"]
    assert "GEMINI_MODEL" in data["recommended_env"]
    assert "ALIBABA_MODEL_REASONING" in data["recommended_env"]
    assert "OPENAI_MODEL_CODER" in data["recommended_env"]
    assert "AGENT_AI_FALLBACK_ORDER" in data["recommended_env"]
    assert "AGENT_AI_TIMEOUT_SECONDS" in data["recommended_env"]
    assert "AGENT_AI_BUDGET_USD_PER_RUN" in data["recommended_env"]
    assert "AGENT_AI_MAX_REMOTE_CALLS" in data["recommended_env"]


def test_setup_validate_supports_anthropic_provider(client: TestClient, tmp_path: Path) -> None:
    payload = {
        "trading_mode": "dry-run",
        "duckdb_path": str(tmp_path / "setup-test-anthropic.duckdb"),
        "vnstock_api_key": "abc1234567890",
        "ssi_consumer_id": "consumer-id",
        "ssi_consumer_secret": "consumer-secret",
        "ssi_account_no": "12345678",
        "ssi_private_key_b64": "dGVzdA==",
        "ai_provider": "anthropic",
        "anthropic_api_key": "sk-ant-12345678901234567890",
        "anthropic_model": "claude-sonnet-4-20250514",
        "ai_model_path": str(tmp_path / "model"),
    }
    response = client.post("/api/setup/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    checks = {item["name"]: item for item in data["checks"]}
    assert checks["agent_ai_provider"]["status"] == "ok"
    assert data["recommended_env"]["AGENT_AI_PROVIDER"] == "anthropic"


def test_setup_validate_supports_gemini_provider(client: TestClient, tmp_path: Path) -> None:
    payload = {
        "trading_mode": "dry-run",
        "duckdb_path": str(tmp_path / "setup-test-gemini.duckdb"),
        "vnstock_api_key": "abc1234567890",
        "ssi_consumer_id": "consumer-id",
        "ssi_consumer_secret": "consumer-secret",
        "ssi_account_no": "12345678",
        "ssi_private_key_b64": "dGVzdA==",
        "ai_provider": "gemini",
        "gemini_api_key": "AIza12345678901234567890",
        "gemini_model": "gemini-2.5-flash",
        "ai_model_path": str(tmp_path / "model"),
    }
    response = client.post("/api/setup/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    checks = {item["name"]: item for item in data["checks"]}
    assert checks["agent_ai_provider"]["status"] == "ok"
    assert data["recommended_env"]["AGENT_AI_PROVIDER"] == "gemini"


def test_setup_validate_supports_alibaba_provider(client: TestClient, tmp_path: Path) -> None:
    payload = {
        "trading_mode": "dry-run",
        "duckdb_path": str(tmp_path / "setup-test-alibaba.duckdb"),
        "vnstock_api_key": "abc1234567890",
        "ssi_consumer_id": "consumer-id",
        "ssi_consumer_secret": "consumer-secret",
        "ssi_account_no": "12345678",
        "ssi_private_key_b64": "dGVzdA==",
        "ai_provider": "alibaba",
        "alibaba_api_key": "sk-alibaba-12345678901234567890",
        "alibaba_base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        "alibaba_model_coder": "qwen3-coder-plus",
        "alibaba_model_reasoning": "qwen3-max",
        "alibaba_model_writing": "qwen3.5-plus",
        "ai_model_path": str(tmp_path / "model"),
    }
    response = client.post("/api/setup/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    checks = {item["name"]: item for item in data["checks"]}
    assert checks["agent_ai_provider"]["status"] == "ok"
    assert data["recommended_env"]["AGENT_AI_PROVIDER"] == "alibaba"


def test_setup_init_local_creates_db(client: TestClient, tmp_path: Path) -> None:
    db_path = tmp_path / "runtime" / "local-trading.duckdb"
    response = client.post("/api/setup/init-local", json={"duckdb_path": str(db_path)})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "initialized"
    assert str(db_path) == data["duckdb_path"]
    assert db_path.exists()


def test_setup_probe_external_contract(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from interface.rest import setup as setup_api

    async def _fake_probe_http(url: str, timeout_seconds: float) -> tuple[bool, str, float]:
        return True, f"HTTP 200 from {url} (timeout={timeout_seconds})", 12.5

    monkeypatch.setattr(setup_api, "_probe_http", _fake_probe_http)
    monkeypatch.setitem(sys.modules, "vnstock", types.SimpleNamespace(__name__="vnstock"))
    model_dir = tmp_path / "models" / "phi-3-mini-int4"
    model_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("OPENVINO_MODEL_PATH", str(model_dir))

    response = client.post(
        "/api/setup/probe-external",
        json={
            "ssi_ping_url": "https://example.com/ssi/ping",
            "vnstock_ping_url": "https://example.com/vnstock/ping",
            "timeout_seconds": 2.0,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data.get("checks"), list)
    names = {item.get("name") for item in data["checks"]}
    assert {"ssi_api", "vnstock_network", "vnstock_sdk", "openvino_model_path"}.issubset(names)
    assert data.get("all_ready") is True


def test_setup_probe_external_warns_when_sources_missing(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from interface.rest import setup as setup_api

    async def _fake_probe_http(url: str, timeout_seconds: float) -> tuple[bool, str, float]:
        return False, f"HTTP 503 from {url} (timeout={timeout_seconds})", 44.0

    monkeypatch.setattr(setup_api, "_probe_http", _fake_probe_http)
    monkeypatch.delitem(sys.modules, "vnstock", raising=False)
    monkeypatch.setenv("OPENVINO_MODEL_PATH", str(tmp_path / "missing-model"))

    response = client.post("/api/setup/probe-external", json={"timeout_seconds": 1.0})
    assert response.status_code == 200
    data = response.json()
    assert data["all_ready"] is False
    assert any(item["status"] == "warn" for item in data["checks"])


def test_setup_model_recommendations_contract(client: TestClient) -> None:
    response = client.get("/api/setup/model-recommendations")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data.get("matrix"), list)
    assert len(data["matrix"]) >= 4
    first = data["matrix"][0]
    assert {"task", "role", "goal", "openai", "anthropic", "gemini", "alibaba"} <= set(first.keys())
