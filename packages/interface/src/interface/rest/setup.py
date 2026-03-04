from __future__ import annotations

import base64
import logging
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
from interface.redaction import redact_mapping, redact_text

router = APIRouter(tags=["setup"])
_AI_PROVIDERS = {"deterministic", "openvino", "openai", "anthropic", "gemini", "alibaba"}
logger = logging.getLogger("interface.setup")
_DEFAULT_AI_FALLBACK_ORDER = "anthropic,gemini,alibaba,deterministic"

_MODEL_RECOMMENDATION_MATRIX: list[dict[str, object]] = [
    {
        "task": "Screener summary",
        "role": "screener",
        "goal": "Fast ranking + concise rationale",
        "openai": "gpt-4o-mini",
        "anthropic": "claude-3-5-haiku-latest",
        "gemini": "gemini-1.5-flash",
        "alibaba": "kimi-k2.5",
    },
    {
        "task": "Technical interpretation",
        "role": "technical",
        "goal": "Explain RSI/MACD/price action conflicts",
        "openai": "gpt-4o-mini",
        "anthropic": "claude-3-5-haiku-latest",
        "gemini": "gemini-1.5-pro",
        "alibaba": "kimi-k2.5",
    },
    {
        "task": "Fundamental thesis",
        "role": "fundamental_thesis",
        "goal": "Narrative + valuation context",
        "openai": "gpt-4o-mini",
        "anthropic": "claude-3-5-sonnet-latest",
        "gemini": "gemini-1.5-pro",
        "alibaba": "kimi-k2.5",
    },
    {
        "task": "Risk challenge",
        "role": "risk_challenge",
        "goal": "Challenge optimistic assumptions",
        "openai": "gpt-4o-mini",
        "anthropic": "claude-3-5-sonnet-latest",
        "gemini": "gemini-1.5-pro",
        "alibaba": "kimi-k2.5",
    },
    {
        "task": "Code/refactor helper",
        "role": "coder",
        "goal": "Implement code and bug fixes",
        "openai": "gpt-4o-mini",
        "anthropic": "claude-3-5-haiku-latest",
        "gemini": "gemini-1.5-flash",
        "alibaba": "qwen2.5-coder-32b-instruct",
    },
    {
        "task": "Docs/UI writing",
        "role": "writing",
        "goal": "Readable docs and UI copy",
        "openai": "gpt-4o-mini",
        "anthropic": "claude-3-5-haiku-latest",
        "gemini": "gemini-1.5-flash",
        "alibaba": "minimax-m2.5",
    },
]


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
        return False, f"Cannot write to {path.parent}: {redact_text(str(exc))}"


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
    ai_provider: Literal["deterministic", "openvino", "openai", "anthropic", "gemini", "alibaba"] = "deterministic"
    openai_api_key: str = Field(default="", max_length=256)
    openai_model: str = Field(default="gpt-4o-mini", max_length=120)
    openai_model_coder: str = Field(default="gpt-4o-mini", max_length=120)
    openai_model_writing: str = Field(default="gpt-4o-mini", max_length=120)
    anthropic_api_key: str = Field(default="", max_length=256)
    anthropic_model: str = Field(default="claude-3-5-haiku-latest", max_length=120)
    anthropic_model_coder: str = Field(default="claude-3-5-haiku-latest", max_length=120)
    anthropic_model_writing: str = Field(default="claude-3-5-haiku-latest", max_length=120)
    gemini_api_key: str = Field(default="", max_length=256)
    gemini_model: str = Field(default="gemini-1.5-flash", max_length=120)
    gemini_model_coder: str = Field(default="gemini-1.5-flash", max_length=120)
    gemini_model_writing: str = Field(default="gemini-1.5-flash", max_length=120)
    alibaba_api_key: str = Field(default="", max_length=256)
    alibaba_base_url: str = Field(default="https://dashscope-intl.aliyuncs.com/compatible-mode/v1", max_length=256)
    alibaba_model_coder: str = Field(default="qwen2.5-coder-32b-instruct", max_length=120)
    alibaba_model_reasoning: str = Field(default="kimi-k2.5", max_length=120)
    alibaba_model_writing: str = Field(default="minimax-m2.5", max_length=120)
    ai_fallback_order: str = Field(default=_DEFAULT_AI_FALLBACK_ORDER, max_length=240)
    ai_timeout_seconds: float = Field(default=20.0, ge=3.0, le=120.0)
    ai_budget_usd_per_run: float = Field(default=0.25, ge=0.01, le=50.0)
    ai_max_remote_calls: int = Field(default=40, ge=1, le=400)
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


def _resolve_ai_provider_ok(
    provider: str,
    *,
    model_exists: bool,
    openai_key_ok: bool,
    anthropic_key_ok: bool,
    gemini_key_ok: bool,
    alibaba_key_ok: bool,
) -> bool:
    if provider == "deterministic":
        return True
    if provider == "openvino":
        return model_exists
    if provider == "openai":
        return openai_key_ok
    if provider == "anthropic":
        return anthropic_key_ok
    if provider == "gemini":
        return gemini_key_ok
    if provider == "alibaba":
        return alibaba_key_ok
    return False


def _provider_ready_detail(provider: str, ok: bool) -> str:
    if ok:
        if provider == "deterministic":
            return "deterministic fallback enabled"
        if provider == "openvino":
            return "OpenVINO model ready"
        if provider == "openai":
            return "OpenAI key configured"
        if provider == "anthropic":
            return "Anthropic key configured"
        if provider == "gemini":
            return "Gemini key configured"
        if provider == "alibaba":
            return "Alibaba key configured"
    if provider == "openvino":
        return "OpenVINO model missing"
    if provider == "openai":
        return "OpenAI key missing/invalid"
    if provider == "anthropic":
        return "Anthropic key missing/invalid"
    if provider == "gemini":
        return "Gemini key missing/invalid"
    if provider == "alibaba":
        return "Alibaba key missing/invalid"
    return "deterministic fallback enabled"


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
        return False, f"Failed request to {url}: {redact_text(str(exc))}", elapsed


def _http_400_from_value_error(exc: ValueError) -> HTTPException:
    safe_detail = redact_text(str(exc))
    logger.warning("Setup profile operation rejected: %s", safe_detail)
    return HTTPException(status_code=400, detail=safe_detail)


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
    openai_model_coder = os.getenv("OPENAI_MODEL_CODER", openai_model or "gpt-4o-mini").strip()
    openai_model_writing = os.getenv("OPENAI_MODEL_WRITING", openai_model or "gpt-4o-mini").strip()
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest").strip()
    anthropic_model_coder = os.getenv(
        "ANTHROPIC_MODEL_CODER",
        anthropic_model or "claude-3-5-haiku-latest",
    ).strip()
    anthropic_model_writing = os.getenv(
        "ANTHROPIC_MODEL_WRITING",
        anthropic_model or "claude-3-5-haiku-latest",
    ).strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
    gemini_model_coder = os.getenv("GEMINI_MODEL_CODER", gemini_model or "gemini-1.5-flash").strip()
    gemini_model_writing = os.getenv("GEMINI_MODEL_WRITING", gemini_model or "gemini-1.5-flash").strip()
    alibaba_key = os.getenv("ALIBABA_API_KEY", "").strip()
    alibaba_model_coder = os.getenv("ALIBABA_MODEL_CODER", "qwen2.5-coder-32b-instruct").strip()
    alibaba_model_reasoning = os.getenv("ALIBABA_MODEL_REASONING", "kimi-k2.5").strip()
    alibaba_model_writing = os.getenv("ALIBABA_MODEL_WRITING", "minimax-m2.5").strip()
    alibaba_base_url = os.getenv("ALIBABA_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1").strip()
    ai_fallback_order = os.getenv("AGENT_AI_FALLBACK_ORDER", _DEFAULT_AI_FALLBACK_ORDER).strip()
    ai_timeout_seconds = float(os.getenv("AGENT_AI_TIMEOUT_SECONDS", "20"))
    ai_budget_usd_per_run = float(os.getenv("AGENT_AI_BUDGET_USD_PER_RUN", "0.25"))
    ai_max_remote_calls = int(os.getenv("AGENT_AI_MAX_REMOTE_CALLS", "40"))
    model_path = Path(os.getenv("OPENVINO_MODEL_PATH", "data/models/phi-3-mini-int4")).expanduser()
    openai_key_ok = len(openai_key) >= 20
    anthropic_key_ok = len(anthropic_key) >= 20
    gemini_key_ok = len(gemini_key) >= 20
    alibaba_key_ok = len(alibaba_key) >= 20
    ai_engine_ready = _resolve_ai_provider_ok(
        ai_provider,
        model_exists=model_path.exists(),
        openai_key_ok=openai_key_ok,
        anthropic_key_ok=anthropic_key_ok,
        gemini_key_ok=gemini_key_ok,
        alibaba_key_ok=alibaba_key_ok,
    )
    cache_integrity_ok = False
    cache_integrity_detail = "Cache integrity check failed"
    try:
        from interface.rest.data_loader import get_cache_runtime_health

        health = get_cache_runtime_health()
        cache_integrity_ok = bool(health.get("ok"))
        cache_integrity_detail = (
            f"schema={health.get('schema_version')} marker={health.get('migration_marker')}"
            if cache_integrity_ok
            else "cache integrity returned non-ok state"
        )
    except Exception as exc:
        cache_integrity_ok = False
        cache_integrity_detail = redact_text(str(exc))
        logger.warning("Cache integrity probe failed in setup/status: %s", cache_integrity_detail)

    checks = [
        _status_line("data_path", writable, writable_detail),
        _status_line("cache_integrity", cache_integrity_ok, cache_integrity_detail),
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
            _provider_ready_detail(ai_provider, ai_engine_ready),
        ),
        _status_line(
            "ai_runtime_policy",
            True,
            (
                f"fallback={ai_fallback_order or 'deterministic'} "
                f"timeout={ai_timeout_seconds:.1f}s "
                f"budget=${ai_budget_usd_per_run:.2f}/run "
                f"max_remote_calls={ai_max_remote_calls}"
            ),
        ),
    ]

    return {
        "mode": mode,
        "data_path": str(data_path),
        "ai_provider": ai_provider,
        "openai_model": openai_model,
        "openai_model_coder": openai_model_coder,
        "openai_model_writing": openai_model_writing,
        "anthropic_model": anthropic_model,
        "anthropic_model_coder": anthropic_model_coder,
        "anthropic_model_writing": anthropic_model_writing,
        "gemini_model": gemini_model,
        "gemini_model_coder": gemini_model_coder,
        "gemini_model_writing": gemini_model_writing,
        "alibaba_base_url": alibaba_base_url,
        "alibaba_model_coder": alibaba_model_coder,
        "alibaba_model_reasoning": alibaba_model_reasoning,
        "alibaba_model_writing": alibaba_model_writing,
        "ai_fallback_order": ai_fallback_order,
        "ai_timeout_seconds": ai_timeout_seconds,
        "ai_budget_usd_per_run": ai_budget_usd_per_run,
        "ai_max_remote_calls": ai_max_remote_calls,
        "checks": checks,
        "all_ready": all(c["status"] == "ok" for c in checks),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/setup/model-recommendations")
async def get_model_recommendations() -> dict[str, object]:
    return {
        "provider_defaults": {
            "openai_reasoning": os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip(),
            "anthropic_reasoning": os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest").strip(),
            "gemini_reasoning": os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip(),
            "alibaba_reasoning": os.getenv("ALIBABA_MODEL_REASONING", "kimi-k2.5").strip(),
            "alibaba_coder": os.getenv("ALIBABA_MODEL_CODER", "qwen2.5-coder-32b-instruct").strip(),
            "alibaba_writing": os.getenv("ALIBABA_MODEL_WRITING", "minimax-m2.5").strip(),
        },
        "matrix": _MODEL_RECOMMENDATION_MATRIX,
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
    anthropic_key_ok = len(payload.anthropic_api_key.strip()) >= 20
    gemini_key_ok = len(payload.gemini_api_key.strip()) >= 20
    alibaba_key_ok = len(payload.alibaba_api_key.strip()) >= 20
    ai_provider = payload.ai_provider if payload.ai_provider in _AI_PROVIDERS else "deterministic"
    ai_provider_ok = _resolve_ai_provider_ok(
        ai_provider,
        model_exists=model_exists,
        openai_key_ok=openai_key_ok,
        anthropic_key_ok=anthropic_key_ok,
        gemini_key_ok=gemini_key_ok,
        alibaba_key_ok=alibaba_key_ok,
    )
    fallback_clean = ",".join([part.strip() for part in payload.ai_fallback_order.split(",") if part.strip()])
    fallback_ok = bool(fallback_clean)
    timeout_ok = payload.ai_timeout_seconds >= 3.0
    budget_ok = payload.ai_budget_usd_per_run >= 0.01
    max_calls_ok = payload.ai_max_remote_calls >= 1

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
            _provider_ready_detail(ai_provider, ai_provider_ok),
        ),
        _status_line("ai_fallback_order", fallback_ok, "Comma-separated provider order for failover"),
        _status_line("ai_timeout_seconds", timeout_ok, "Per-call timeout in seconds"),
        _status_line("ai_budget_usd_per_run", budget_ok, "Estimated remote AI cost cap per run"),
        _status_line("ai_max_remote_calls", max_calls_ok, "Max remote AI calls per run"),
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
            "OPENAI_MODEL_CODER": payload.openai_model_coder or payload.openai_model,
            "OPENAI_MODEL_WRITING": payload.openai_model_writing or payload.openai_model,
            "ANTHROPIC_API_KEY": "***" if payload.anthropic_api_key else "",
            "ANTHROPIC_MODEL": payload.anthropic_model,
            "ANTHROPIC_MODEL_CODER": payload.anthropic_model_coder or payload.anthropic_model,
            "ANTHROPIC_MODEL_WRITING": payload.anthropic_model_writing or payload.anthropic_model,
            "GEMINI_API_KEY": "***" if payload.gemini_api_key else "",
            "GEMINI_MODEL": payload.gemini_model,
            "GEMINI_MODEL_CODER": payload.gemini_model_coder or payload.gemini_model,
            "GEMINI_MODEL_WRITING": payload.gemini_model_writing or payload.gemini_model,
            "ALIBABA_API_KEY": "***" if payload.alibaba_api_key else "",
            "ALIBABA_BASE_URL": payload.alibaba_base_url,
            "ALIBABA_MODEL_CODER": payload.alibaba_model_coder,
            "ALIBABA_MODEL_REASONING": payload.alibaba_model_reasoning,
            "ALIBABA_MODEL_WRITING": payload.alibaba_model_writing,
            "AGENT_AI_FALLBACK_ORDER": fallback_clean or "deterministic",
            "AGENT_AI_TIMEOUT_SECONDS": payload.ai_timeout_seconds,
            "AGENT_AI_BUDGET_USD_PER_RUN": payload.ai_budget_usd_per_run,
            "AGENT_AI_MAX_REMOTE_CALLS": payload.ai_max_remote_calls,
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
        raise _http_400_from_value_error(exc) from exc


@router.post("/setup/profiles/decrypt")
async def decrypt_profile(payload: ProfileDecryptRequest) -> dict[str, object]:
    try:
        config = profile_vault.decrypt_profile(payload.profile_name, payload.passphrase)
        return {"success": True, "profile_name": payload.profile_name, "config": redact_mapping(config)}
    except ValueError as exc:
        raise _http_400_from_value_error(exc) from exc


@router.post("/setup/profiles/activate")
async def activate_profile(payload: ProfileActivateRequest) -> dict[str, object]:
    try:
        result = profile_vault.activate_profile(payload.profile_name)
        return {"success": True, **result}
    except ValueError as exc:
        raise _http_400_from_value_error(exc) from exc


@router.get("/setup/profiles/{profile_name}/export")
async def export_profile(profile_name: str) -> dict[str, object]:
    try:
        payload_b64 = profile_vault.export_profile(profile_name)
        return {"success": True, "profile_name": profile_name, "payload_b64": payload_b64}
    except ValueError as exc:
        raise _http_400_from_value_error(exc) from exc


@router.post("/setup/profiles/import")
async def import_profile(payload: ProfileImportRequest) -> dict[str, object]:
    try:
        result = profile_vault.import_profile(payload.profile_name, payload.payload_b64, set_active=payload.set_active)
        return {"success": True, **result}
    except ValueError as exc:
        raise _http_400_from_value_error(exc) from exc


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
        raise _http_400_from_value_error(exc) from exc


@router.post("/setup/profiles/revoke")
async def revoke_profile(payload: ProfileRevokeRequest) -> dict[str, object]:
    try:
        result = profile_vault.revoke_profile(payload.profile_name)
        return {"success": True, **result}
    except ValueError as exc:
        raise _http_400_from_value_error(exc) from exc


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
        checks.append(_probe_line("vnstock_sdk", False, f"vnstock import failed: {redact_text(str(exc))}"))

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
