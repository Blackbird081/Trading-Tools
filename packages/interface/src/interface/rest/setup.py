from __future__ import annotations

import base64
import os
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Literal

import duckdb
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(tags=["setup"])


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
    ai_model_path: str = Field(default="data/models/phi-3-mini-int4", max_length=256)


class SetupInitRequest(BaseModel):
    duckdb_path: str | None = Field(default=None, max_length=256)


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
    model_path = Path(os.getenv("OPENVINO_MODEL_PATH", "data/models/phi-3-mini-int4")).expanduser()
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
    ]

    return {
        "mode": mode,
        "data_path": str(data_path),
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
