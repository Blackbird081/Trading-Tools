from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes


@dataclass(slots=True)
class ProfileRecord:
    name: str
    file: str
    revoked: bool
    created_at: str
    updated_at: str


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _profiles_root() -> Path:
    raw = os.getenv("TRADING_PROFILE_DIR", "").strip()
    if raw:
        root = Path(raw).expanduser()
    else:
        root = Path.home() / ".trading" / "profiles"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _index_file() -> Path:
    return _profiles_root() / "profiles_index.json"


def _profile_file(name: str) -> Path:
    cleaned = name.strip().lower().replace(" ", "-")
    return _profiles_root() / f"{cleaned}.profile.enc"


def _load_index() -> dict[str, Any]:
    path = _index_file()
    if not path.exists():
        return {"active_profile": None, "profiles": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"active_profile": None, "profiles": {}}


def _save_index(payload: dict[str, Any]) -> None:
    _index_file().write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _derive_key(passphrase: str, salt: bytes, iterations: int = 200_000) -> bytes:
    return PBKDF2(passphrase.encode("utf-8"), salt, dkLen=32, count=iterations, hmac_hash_module=SHA256)


def _encrypt_payload(payload: dict[str, Any], passphrase: str) -> dict[str, Any]:
    salt = get_random_bytes(16)
    nonce = get_random_bytes(12)
    key = _derive_key(passphrase, salt)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    plaintext = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    return {
        "kdf": {"name": "PBKDF2-HMAC-SHA256", "iterations": 200_000, "salt_b64": base64.b64encode(salt).decode("ascii")},
        "cipher": "AES-256-GCM",
        "nonce_b64": base64.b64encode(nonce).decode("ascii"),
        "tag_b64": base64.b64encode(tag).decode("ascii"),
        "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
        "encrypted_at": _now_iso(),
    }


def _decrypt_payload(blob: dict[str, Any], passphrase: str) -> dict[str, Any]:
    kdf = blob.get("kdf", {})
    iterations = int(kdf.get("iterations", 200_000))
    salt = base64.b64decode(str(kdf.get("salt_b64", "")))
    nonce = base64.b64decode(str(blob.get("nonce_b64", "")))
    tag = base64.b64decode(str(blob.get("tag_b64", "")))
    ciphertext = base64.b64decode(str(blob.get("ciphertext_b64", "")))
    key = _derive_key(passphrase, salt=salt, iterations=iterations)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    plaintext = cipher.decrypt_and_verify(ciphertext, tag)
    return json.loads(plaintext.decode("utf-8"))


def list_profiles() -> dict[str, Any]:
    idx = _load_index()
    records: list[ProfileRecord] = []
    for name, info in idx.get("profiles", {}).items():
        records.append(
            ProfileRecord(
                name=name,
                file=str(info.get("file", "")),
                revoked=bool(info.get("revoked", False)),
                created_at=str(info.get("created_at", "")),
                updated_at=str(info.get("updated_at", "")),
            )
        )
    return {"active_profile": idx.get("active_profile"), "profiles": [r.__dict__ for r in records]}


def create_profile(name: str, passphrase: str, config: dict[str, Any]) -> dict[str, Any]:
    if len(passphrase) < 8:
        msg = "Passphrase must be at least 8 characters."
        raise ValueError(msg)
    path = _profile_file(name)
    if path.exists():
        msg = f"Profile '{name}' already exists."
        raise ValueError(msg)

    blob = _encrypt_payload(config, passphrase)
    path.write_text(json.dumps(blob, ensure_ascii=False, indent=2), encoding="utf-8")

    idx = _load_index()
    now = _now_iso()
    idx.setdefault("profiles", {})[name] = {
        "file": path.name,
        "revoked": False,
        "created_at": now,
        "updated_at": now,
    }
    if not idx.get("active_profile"):
        idx["active_profile"] = name
    _save_index(idx)
    return {"name": name, "active_profile": idx.get("active_profile"), "created_at": now}


def decrypt_profile(name: str, passphrase: str) -> dict[str, Any]:
    idx = _load_index()
    info = idx.get("profiles", {}).get(name)
    if not info:
        msg = f"Profile '{name}' not found."
        raise ValueError(msg)
    if bool(info.get("revoked", False)):
        msg = f"Profile '{name}' is revoked."
        raise ValueError(msg)
    path = _profiles_root() / str(info.get("file"))
    if not path.exists():
        msg = f"Profile file missing for '{name}'."
        raise ValueError(msg)
    blob = json.loads(path.read_text(encoding="utf-8"))
    return _decrypt_payload(blob, passphrase)


def activate_profile(name: str) -> dict[str, Any]:
    idx = _load_index()
    profiles = idx.get("profiles", {})
    if name not in profiles:
        msg = f"Profile '{name}' not found."
        raise ValueError(msg)
    if bool(profiles[name].get("revoked", False)):
        msg = f"Profile '{name}' is revoked."
        raise ValueError(msg)
    idx["active_profile"] = name
    _save_index(idx)
    return {"active_profile": name}


def export_profile(name: str) -> str:
    idx = _load_index()
    info = idx.get("profiles", {}).get(name)
    if not info:
        msg = f"Profile '{name}' not found."
        raise ValueError(msg)
    path = _profiles_root() / str(info.get("file"))
    if not path.exists():
        msg = f"Profile file missing for '{name}'."
        raise ValueError(msg)
    raw = path.read_bytes()
    wrapper = {
        "name": name,
        "file": path.name,
        "blob_b64": base64.b64encode(raw).decode("ascii"),
        "exported_at": _now_iso(),
    }
    return base64.b64encode(json.dumps(wrapper, ensure_ascii=False).encode("utf-8")).decode("ascii")


def import_profile(name: str, payload_b64: str, set_active: bool = False) -> dict[str, Any]:
    wrapper_raw = base64.b64decode(payload_b64.encode("ascii"))
    wrapper = json.loads(wrapper_raw.decode("utf-8"))
    blob_raw = base64.b64decode(str(wrapper.get("blob_b64", "")).encode("ascii"))

    path = _profile_file(name)
    path.write_bytes(blob_raw)

    idx = _load_index()
    now = _now_iso()
    idx.setdefault("profiles", {})[name] = {
        "file": path.name,
        "revoked": False,
        "created_at": now,
        "updated_at": now,
    }
    if set_active:
        idx["active_profile"] = name
    _save_index(idx)
    return {"name": name, "active_profile": idx.get("active_profile")}


def rotate_profile_passphrase(name: str, old_passphrase: str, new_passphrase: str) -> dict[str, Any]:
    if len(new_passphrase) < 8:
        msg = "New passphrase must be at least 8 characters."
        raise ValueError(msg)
    payload = decrypt_profile(name, old_passphrase)
    idx = _load_index()
    info = idx.get("profiles", {}).get(name)
    if not info:
        msg = f"Profile '{name}' not found."
        raise ValueError(msg)
    path = _profiles_root() / str(info.get("file"))
    blob = _encrypt_payload(payload, new_passphrase)
    path.write_text(json.dumps(blob, ensure_ascii=False, indent=2), encoding="utf-8")
    info["updated_at"] = _now_iso()
    _save_index(idx)
    return {"name": name, "updated_at": info["updated_at"]}


def revoke_profile(name: str) -> dict[str, Any]:
    idx = _load_index()
    profiles = idx.get("profiles", {})
    if name not in profiles:
        msg = f"Profile '{name}' not found."
        raise ValueError(msg)
    profiles[name]["revoked"] = True
    profiles[name]["updated_at"] = _now_iso()
    if idx.get("active_profile") == name:
        idx["active_profile"] = None
    _save_index(idx)
    return {"name": name, "revoked": True}
