from __future__ import annotations

from pathlib import Path

import pytest

import interface.profile_vault as profile_vault


@pytest.fixture
def isolated_profile_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "profiles"
    monkeypatch.setenv("TRADING_PROFILE_DIR", str(root))
    return root


def test_list_profiles_handles_corrupted_index(isolated_profile_dir: Path) -> None:
    index = isolated_profile_dir / "profiles_index.json"
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text("{bad-json", encoding="utf-8")

    payload = profile_vault.list_profiles()
    assert payload["active_profile"] is None
    assert payload["profiles"] == []


def test_create_profile_validates_passphrase_and_duplicate(isolated_profile_dir: Path) -> None:
    with pytest.raises(ValueError, match="at least 8 characters"):
        profile_vault.create_profile("short", "1234567", {"trading_mode": "dry-run"})

    created = profile_vault.create_profile("demo", "very-strong-passphrase", {"trading_mode": "dry-run"})
    assert created["active_profile"] == "demo"

    with pytest.raises(ValueError, match="already exists"):
        profile_vault.create_profile("demo", "very-strong-passphrase", {"trading_mode": "dry-run"})


def test_profile_error_paths_and_active_cleanup(isolated_profile_dir: Path) -> None:
    with pytest.raises(ValueError, match="not found"):
        profile_vault.decrypt_profile("missing", "passphrase")
    with pytest.raises(ValueError, match="not found"):
        profile_vault.activate_profile("missing")
    with pytest.raises(ValueError, match="not found"):
        profile_vault.export_profile("missing")
    with pytest.raises(ValueError, match="not found"):
        profile_vault.revoke_profile("missing")

    profile_vault.create_profile("demo", "very-strong-passphrase", {"trading_mode": "dry-run"})
    profile_vault.revoke_profile("demo")
    listed = profile_vault.list_profiles()
    assert listed["active_profile"] is None

    with pytest.raises(ValueError, match="is revoked"):
        profile_vault.decrypt_profile("demo", "very-strong-passphrase")
    with pytest.raises(ValueError, match="is revoked"):
        profile_vault.activate_profile("demo")


def test_missing_file_and_rotate_edge_cases(
    isolated_profile_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile_vault.create_profile("demo", "very-strong-passphrase", {"trading_mode": "dry-run"})
    idx = profile_vault._load_index()  # noqa: SLF001
    demo_file = isolated_profile_dir / str(idx["profiles"]["demo"]["file"])
    demo_file.unlink()

    with pytest.raises(ValueError, match="file missing"):
        profile_vault.decrypt_profile("demo", "very-strong-passphrase")
    with pytest.raises(ValueError, match="file missing"):
        profile_vault.export_profile("demo")

    with pytest.raises(ValueError, match="at least 8 characters"):
        profile_vault.rotate_profile_passphrase("demo", "old", "short")

    monkeypatch.setattr(profile_vault, "decrypt_profile", lambda *_args, **_kwargs: {"trading_mode": "dry-run"})
    monkeypatch.setattr(profile_vault, "_load_index", lambda: {"active_profile": None, "profiles": {}})
    with pytest.raises(ValueError, match="not found"):
        profile_vault.rotate_profile_passphrase("ghost", "very-strong-passphrase", "another-strong-passphrase")
