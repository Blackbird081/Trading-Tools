from __future__ import annotations

import base64
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Literal

import duckdb
from fastapi import APIRouter, HTTPException
import httpx
from pydantic import BaseModel, Field

from interface import profile_vault

router = APIRouter(tags=["setup"])
_AI_PROVIDERS = {"deterministic", "openvino", "openai"}


def _to_mode(raw_mode: str, raw_dry_run: str) -> Literal["dry-run", "live"]:
    mode = raw_mode.strip().lower()
    if mode in {"dry-run", "live"}:
        return mode  # type: ignore[return-value]
    dry = raw_dry_run.strip().lower() in {"1", "true", "yes", "on"}
    return "dry-run" if dry else "live"


def _safe_write_probe(path: Path) -> tuple[bool, str]:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            mode="w",
            prefix=".probe-",
            suffix=".tmp",
            dir=str(path.parent),
            delete=True,
            encoding="utf-8",
        ) as probe:
            probe.write("ok")
            probe.flush()
        return True, f"Writable parent: {path.parent}"
    except Exception as exc:  # pragma: no cover - env-dependent permission
        return False, f"Cannot write to {path.parent}: {exc}"


def _looks_like_b64(value: str) -> bool:
    raw = value.strip()
    if not raw:
        return False
    try:
        base64.b64decode(raw, validate=True)
        return True
    except Exception:
        return False


def _status_line(name: str, ok: bool, detail: str) -> dict[str, str]:
    return {
        "name": name,
        "status": "ok" if ok else "warn",
        "detail": detail,
    }


def _resolve_data_path(env_path: str = "") -> Path:
    raw = env_path.strip() or os.getenv("DUCKDB_PATH", "data/trading.duckdb").strip()
    return Path(raw).expanduser()


class SetupValidateRequest(BaseModel):
    trading_mode: Literal["dry-run", "live"] = "dry-run"
    duckdb_path: str = Field(default="data/trading.duckdb", min_length=3, max_length=256)
    vnstock_api_key: str = Field(default="", max_length=256)
    ssi_consumer_id: str = Field(default="", max_length=128)
    ssi_consumer_secret: str = Field(default="", max_length=256)
    ssi_account_no: str = Field(default="", max_length=32)
    ssi_private_key_b64: str = Field(default="", max_length=16384)
    ai_provider: Literal["deterministic", "openvino", "openai"] = "deterministic"
    openai_api_key: str = Field(default="", max_length=256)
    openai_model: str = Field(default="gpt-4o-mini", max_length=120)
    ai_model_path: str = Field(default="data/models/phi-3-mini-int4", max_length=256)


class SetupInitRequest(BaseModel):
    duckdb_path: str | None = Field(default=None, max_length=256)


class ProfileCreateRequest(BaseModel):
    profile_name: str = Field(min_length=2, max_length=64)
    passphrase: str = Field(min_length=8, max_length=256)
    config: dict[str, object] = Field(default_factory=dict)
    set_active: bool = True


class ProfileDecryptRequest(BaseModel):
    profile_name: str = Field(min_length=2, max_length=64)
    passphrase: str = Field(min_length=8, max_length=256)


class ProfileActivateRequest(BaseModel):
    profile_name: str = Field(min_length=2, max_length=64)


class ProfileImportRequest(BaseModel):
    profile_name: str = Field(min_length=2, max_length=64)
    payload_b64: str = Field(min_length=10)
    set_active: bool = False


class ProfileRotateRequest(BaseModel):
    profile_name: str = Field(min_length=2, max_length=64)
    old_passphrase: str = Field(min_length=8, max_length=256)
    new_passphrase: str = Field(min_length=8, max_length=256)


class ProfileRevokeRequest(BaseModel):
    profile_name: str = Field(min_length=2, max_length=64)


class ExternalProbeRequest(BaseModel):
    ssi_ping_url: str = Field(default="https://fc-tradeapi.ssi.com.vn/api/v2/Trading/ping", max_length=256)
    vnstock_ping_url: str = Field(default="https://api.vndirect.com.vn", max_length=256)
    timeout_seconds: float = Field(default=5.0, ge=1.0, le=20.0)


def _probe_line(name: str, ok: bool, detail: str, latency_ms: float | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": name,
        "status": "ok" if ok else "warn",
        "detail": detail,
    }
    if latency_ms is not None:
        payload["latency_ms"] = round(latency_ms, 1)
    return payload


async def _probe_http(url: str, timeout_seconds: float) -> tuple[bool, str, float]:
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(url, follow_redirects=True)
        elapsed = (time.perf_counter() - start) * 1000
        ok = response.status_code < 500
        detail = f"HTTP {response.status_code} from {url}"
        return ok, detail, elapsed
    except Exception as exc:  # pragma: no cover - network-dependent
        elapsed = (time.perf_counter() - start) * 1000
        return False, f"Failed request to {url}: {exc}", elapsed


@router.get("/setup/status")
async def get_setup_status() -> dict[str, object]:
    mode = _to_mode(os.getenv("TRADING_MODE", ""), os.getenv("DRY_RUN", "true"))
    data_path = _resolve_data_path()
    writable, writable_detail = _safe_write_probe(data_path)

    vnstock_key = os.getenv("VNSTOCK_API_KEY", "")
    ssi_ready = all(
        [
            os.getenv("SSI_CONSUMER_ID", "").strip(),
            os.getenv("SSI_CONSUMER_SECRET", "").strip(),
            os.getenv("SSI_ACCOUNT_NO", "").strip(),
        ]
    )
    has_private_key = bool(
        os.getenv("SSI_PRIVATE_KEY_B64", "").strip() or os.getenv("SSI_PRIVATE_KEY_PEM", "").strip()
    )
    ai_provider = os.getenv("AGENT_AI_PROVIDER", "deterministic").strip().lower()
    if ai_provider not in _AI_PROVIDERS:
        ai_provider = "deterministic"
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
    model_path = Path(os.getenv("OPENVINO_MODEL_PATH", "data/models/phi-3-mini-int4")).expanduser()
    ai_engine_ready = (
        (ai_provider == "deterministic")
        or (ai_provider == "openvino" and model_path.exists())
        or (ai_provider == "openai" and len(openai_key) >= 20)
    )
    checks = [
        _status_line("data_path", writable, writable_detail),
        _status_line("vnstock_api_key", bool(vnstock_key.strip()), "Configured" if vnstock_key.strip() else "Missing"),
        _status_line(
            "ssi_credentials",
            bool(ssi_ready and has_private_key),
            "Configured"
            if ssi_ready and has_private_key
            else "Need SSI_CONSUMER_ID/SECRET/ACCOUNT_NO and private key",
        ),
        _status_line(
            "ai_model_path",
            model_path.exists(),
            f"{model_path} {'exists' if model_path.exists() else 'not found'}",
        ),
        _status_line(
            "agent_ai_provider",
            ai_engine_ready,
            (
                "deterministic fallback enabled"
                if ai_provider == "deterministic"
                else ("OpenVINO model ready" if ai_provider == "openvino" else "OpenAI key configured")
            )
            if ai_engine_ready
            else (
                "OpenVINO model missing"
                if ai_provider == "openvino"
                else "OpenAI key missing/invalid"
            ),
        ),
    ]

    return {
        "mode": mode,
        "data_path": str(data_path),
        "ai_provider": ai_provider,
        "openai_model": openai_model,
        "checks": checks,
        "all_ready": all(c["status"] == "ok" for c in checks),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.post("/setup/validate")
async def validate_setup(payload: SetupValidateRequest) -> dict[str, object]:
    data_path = _resolve_data_path(payload.duckdb_path)
    writable, writable_detail = _safe_write_probe(data_path)
    model_exists = Path(payload.ai_model_path).expanduser().exists()
    ssi_key_ok = len(payload.ssi_consumer_id.strip()) >= 6 and len(payload.ssi_consumer_secret.strip()) >= 8
    account_ok = payload.ssi_account_no.strip().isdigit() and 6 <= len(payload.ssi_account_no.strip()) <= 20
    private_key_ok = _looks_like_b64(payload.ssi_private_key_b64)
    vnstock_ok = len(payload.vnstock_api_key.strip()) >= 10
    openai_key_ok = len(payload.openai_api_key.strip()) >= 20
    ai_provider = payload.ai_provider if payload.ai_provider in _AI_PROVIDERS else "deterministic"
    ai_provider_ok = (
        ai_provider == "deterministic"
        or (ai_provider == "openvino" and model_exists)
        or (ai_provider == "openai" and openai_key_ok)
    )

    checks = [
        _status_line("duckdb_path", writable, writable_detail),
        _status_line("vnstock_api_key", vnstock_ok, "Length >= 10 expected"),
        _status_line(
            "ssi_consumer",
            ssi_key_ok,
            "Consumer ID/Secret format looks valid" if ssi_key_ok else "Invalid SSI consumer credentials format",
        ),
        _status_line("ssi_account_no", account_ok, "Digits only, length 6-20"),
        _status_line("ssi_private_key_b64", private_key_ok, "Base64 decode check"),
        _status_line(
            "ai_model_path",
            model_exists,
            f"{payload.ai_model_path} {'exists' if model_exists else 'not found (CPU fallback still possible)'}",
        ),
        _status_line(
            "agent_ai_provider",
            ai_provider_ok,
            (
                "deterministic fallback enabled"
                if ai_provider == "deterministic"
                else ("openvino model is available" if ai_provider == "openvino" else "OpenAI key length >= 20")
            ),
        ),
        _status_line(
            "trading_mode",
            payload.trading_mode == "dry-run",
            "dry-run recommended for initial setup" if payload.trading_mode == "dry-run" else "live mode requires extra safeguards",
        ),
    ]

    return {
        "valid": all(c["status"] == "ok" for c in checks[:-1]) and payload.trading_mode in {"dry-run", "live"},
        "checks": checks,
        "recommended_env": {
            "TRADING_MODE": payload.trading_mode,
            "DUCKDB_PATH": str(data_path),
            "VNSTOCK_API_KEY": "***" if payload.vnstock_api_key else "",
            "SSI_CONSUMER_ID": payload.ssi_consumer_id,
            "SSI_CONSUMER_SECRET": "***" if payload.ssi_consumer_secret else "",
            "SSI_ACCOUNT_NO": payload.ssi_account_no,
            "SSI_PRIVATE_KEY_B64": "***" if payload.ssi_private_key_b64 else "",
            "AGENT_AI_PROVIDER": ai_provider,
            "OPENAI_API_KEY": "***" if payload.openai_api_key else "",
            "OPENAI_MODEL": payload.openai_model,
            "OPENVINO_MODEL_PATH": payload.ai_model_path,
        },
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.post("/setup/init-local")
async def init_local_runtime(payload: SetupInitRequest) -> dict[str, object]:
    db_path = _resolve_data_path(payload.duckdb_path or "")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS setup_metadata (
                key VARCHAR PRIMARY KEY,
                value VARCHAR NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO setup_metadata (key, value, updated_at)
            VALUES ('initialized', 'true', ?)
            ON CONFLICT (key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            [datetime.now(UTC)],
        )
    finally:
        conn.close()

    return {
        "status": "initialized",
        "duckdb_path": str(db_path),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/setup/profiles")
async def get_profiles() -> dict[str, object]:
    return profile_vault.list_profiles()


@router.post("/setup/profiles/create")
async def create_profile(payload: ProfileCreateRequest) -> dict[str, object]:
    try:
        created = profile_vault.create_profile(payload.profile_name, payload.passphrase, payload.config)
        if payload.set_active:
            profile_vault.activate_profile(payload.profile_name)
        profiles = profile_vault.list_profiles()
        return {"success": True, "created": created, "active_profile": profiles.get("active_profile")}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/setup/profiles/decrypt")
async def decrypt_profile(payload: ProfileDecryptRequest) -> dict[str, object]:
    try:
        config = profile_vault.decrypt_profile(payload.profile_name, payload.passphrase)
        return {"success": True, "profile_name": payload.profile_name, "config": config}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/setup/profiles/activate")
async def activate_profile(payload: ProfileActivateRequest) -> dict[str, object]:
    try:
        result = profile_vault.activate_profile(payload.profile_name)
        return {"success": True, **result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/setup/profiles/{profile_name}/export")
async def export_profile(profile_name: str) -> dict[str, object]:
    try:
        payload_b64 = profile_vault.export_profile(profile_name)
        return {"success": True, "profile_name": profile_name, "payload_b64": payload_b64}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/setup/profiles/import")
async def import_profile(payload: ProfileImportRequest) -> dict[str, object]:
    try:
        result = profile_vault.import_profile(payload.profile_name, payload.payload_b64, set_active=payload.set_active)
        return {"success": True, **result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/setup/profiles/rotate")
async def rotate_profile(payload: ProfileRotateRequest) -> dict[str, object]:
    try:
        result = profile_vault.rotate_profile_passphrase(
            payload.profile_name,
            payload.old_passphrase,
            payload.new_passphrase,
        )
        return {"success": True, **result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/setup/profiles/revoke")
async def revoke_profile(payload: ProfileRevokeRequest) -> dict[str, object]:
    try:
        result = profile_vault.revoke_profile(payload.profile_name)
        return {"success": True, **result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/setup/probe-external")
async def probe_external_connections(payload: ExternalProbeRequest) -> dict[str, object]:
    checks: list[dict[str, object]] = []

    ssi_ok, ssi_detail, ssi_latency = await _probe_http(payload.ssi_ping_url, payload.timeout_seconds)
    checks.append(_probe_line("ssi_api", ssi_ok, ssi_detail, ssi_latency))

    vn_ok, vn_detail, vn_latency = await _probe_http(payload.vnstock_ping_url, payload.timeout_seconds)
    checks.append(_probe_line("vnstock_network", vn_ok, vn_detail, vn_latency))

    try:
        import vnstock  # noqa: F401  # type: ignore[import-untyped]

        checks.append(_probe_line("vnstock_sdk", True, "vnstock module import succeeded"))
    except Exception as exc:
        checks.append(_probe_line("vnstock_sdk", False, f"vnstock import failed: {exc}"))

    model_path = Path(os.getenv("OPENVINO_MODEL_PATH", "data/models/phi-3-mini-int4")).expanduser()
    model_ok = model_path.exists()
    checks.append(
        _probe_line(
            "openvino_model_path",
            model_ok,
            f"{model_path} {'exists' if model_ok else 'missing'}",
        ),
    )

    return {
        "checks": checks,
        "all_ready": all(c["status"] == "ok" for c in checks),
        "timestamp": datetime.now(UTC).isoformat(),
    }
