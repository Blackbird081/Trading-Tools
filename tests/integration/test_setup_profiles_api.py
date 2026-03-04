from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from interface.app import create_app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("TRADING_PROFILE_DIR", str(tmp_path / "profiles"))
    return TestClient(create_app())


def test_profile_vault_end_to_end(client: TestClient) -> None:
    create = client.post(
        "/api/setup/profiles/create",
        json={
            "profile_name": "demo",
            "passphrase": "very-strong-passphrase",
            "config": {
                "trading_mode": "dry-run",
                "vnstock_api_key": "abc1234567890",
            },
            "set_active": True,
        },
    )
    assert create.status_code == 200
    assert create.json()["success"] is True

    listed = client.get("/api/setup/profiles")
    assert listed.status_code == 200
    payload = listed.json()
    assert payload["active_profile"] == "demo"
    assert any(item["name"] == "demo" for item in payload["profiles"])

    decrypt = client.post(
        "/api/setup/profiles/decrypt",
        json={"profile_name": "demo", "passphrase": "very-strong-passphrase"},
    )
    assert decrypt.status_code == 200
    assert decrypt.json()["config"]["trading_mode"] == "dry-run"
    assert decrypt.json()["config"]["vnstock_api_key"] == "***REDACTED***"

    export = client.get("/api/setup/profiles/demo/export")
    assert export.status_code == 200
    blob = export.json()["payload_b64"]
    assert isinstance(blob, str) and len(blob) > 20

    rotate = client.post(
        "/api/setup/profiles/rotate",
        json={
            "profile_name": "demo",
            "old_passphrase": "very-strong-passphrase",
            "new_passphrase": "new-strong-passphrase",
        },
    )
    assert rotate.status_code == 200
    assert rotate.json()["success"] is True

    decrypt_new = client.post(
        "/api/setup/profiles/decrypt",
        json={"profile_name": "demo", "passphrase": "new-strong-passphrase"},
    )
    assert decrypt_new.status_code == 200

    imported = client.post(
        "/api/setup/profiles/import",
        json={
            "profile_name": "backup",
            "payload_b64": blob,
            "set_active": True,
        },
    )
    assert imported.status_code == 200
    assert imported.json()["active_profile"] == "backup"

    revoke = client.post("/api/setup/profiles/revoke", json={"profile_name": "demo"})
    assert revoke.status_code == 200
    assert revoke.json()["success"] is True

    activate_revoked = client.post("/api/setup/profiles/activate", json={"profile_name": "demo"})
    assert activate_revoked.status_code == 400


def test_profile_decrypt_wrong_passphrase_returns_400(client: TestClient) -> None:
    created = client.post(
        "/api/setup/profiles/create",
        json={
            "profile_name": "wrong-pass",
            "passphrase": "correct-passphrase",
            "config": {"trading_mode": "dry-run"},
            "set_active": False,
        },
    )
    assert created.status_code == 200

    decrypt = client.post(
        "/api/setup/profiles/decrypt",
        json={"profile_name": "wrong-pass", "passphrase": "incorrect-passphrase"},
    )
    assert decrypt.status_code == 400


def test_profile_create_error_is_redacted(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from interface.rest import setup as setup_api

    def _raise_secret(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise ValueError("api_key=sk-test-secret-123")

    monkeypatch.setattr(setup_api.profile_vault, "create_profile", _raise_secret)
    response = client.post(
        "/api/setup/profiles/create",
        json={
            "profile_name": "demo2",
            "passphrase": "very-strong-passphrase",
            "config": {},
            "set_active": False,
        },
    )
    assert response.status_code == 400
    detail = response.json().get("detail", "")
    assert "***REDACTED***" in detail
    assert "sk-test-secret-123" not in detail
