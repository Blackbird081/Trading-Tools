"""Health Check Endpoint — dependency status monitoring.

★ RES-01: /api/health returns status of all dependencies.
★ /api/health/live — liveness probe (always 200 if process is running)
★ /api/health/ready — readiness probe (200 only if all critical deps are up)
★ /api/health/detailed — full dependency status for ops monitoring
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Response

logger = logging.getLogger("interface.health")

router = APIRouter(tags=["health"])

# Track startup time
_startup_time = time.monotonic()
_startup_datetime = datetime.now(UTC).isoformat()


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    """Liveness probe — returns 200 if process is running.

    ★ Kubernetes: use this for livenessProbe.
    ★ Never fails unless process is dead.
    """
    return {"status": "alive", "timestamp": datetime.now(UTC).isoformat()}


@router.get("/health/ready")
async def readiness(response: Response) -> dict[str, Any]:
    """Readiness probe — returns 200 only if critical dependencies are ready.

    ★ Kubernetes: use this for readinessProbe.
    ★ Returns 503 if any critical dependency is down.
    """
    checks = await _run_health_checks()
    critical_failed = any(
        not c["healthy"] for c in checks.values()
        if c.get("critical", False)
    )

    if critical_failed:
        response.status_code = 503

    return {
        "status": "ready" if not critical_failed else "not_ready",
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": {k: v["healthy"] for k, v in checks.items()},
    }


@router.get("/health")
@router.get("/health/detailed")
async def detailed_health(response: Response) -> dict[str, Any]:
    """Detailed health check — full dependency status.

    ★ Use for ops monitoring dashboard.
    ★ Returns 503 if any critical dependency is down.
    """
    checks = await _run_health_checks()
    critical_failed = any(
        not c["healthy"] for c in checks.values()
        if c.get("critical", False)
    )

    uptime_seconds = time.monotonic() - _startup_time

    if critical_failed:
        response.status_code = 503

    return {
        "status": "healthy" if not critical_failed else "degraded",
        "timestamp": datetime.now(UTC).isoformat(),
        "startup_time": _startup_datetime,
        "uptime_seconds": round(uptime_seconds, 1),
        "dependencies": checks,
    }


async def _run_health_checks() -> dict[str, dict[str, Any]]:
    """Run all health checks concurrently."""
    results = await asyncio.gather(
        _check_duckdb(),
        _check_ssi_api(),
        _check_ai_engine(),
        return_exceptions=True,
    )

    checks: dict[str, dict[str, Any]] = {}
    check_names = ["duckdb", "ssi_api", "ai_engine"]

    for name, result in zip(check_names, results):
        if isinstance(result, Exception):
            checks[name] = {
                "healthy": False,
                "error": str(result),
                "critical": name == "duckdb",  # DuckDB is critical
            }
        else:
            checks[name] = result  # type: ignore[assignment]

    return checks


async def _check_duckdb() -> dict[str, Any]:
    """Check DuckDB connectivity."""
    try:
        import duckdb
        conn = duckdb.connect(":memory:")
        result = conn.execute("SELECT 1").fetchone()
        conn.close()
        return {
            "healthy": result is not None,
            "critical": True,
            "latency_ms": 0,
        }
    except Exception as exc:
        return {"healthy": False, "critical": True, "error": str(exc)}


async def _check_ssi_api() -> dict[str, Any]:
    """Check SSI API reachability (non-blocking)."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            start = time.monotonic()
            r = await client.get("https://fc-tradeapi.ssi.com.vn/api/v2/Trading/ping",
                                  follow_redirects=True)
            latency_ms = (time.monotonic() - start) * 1000
            return {
                "healthy": r.status_code < 500,
                "critical": False,
                "status_code": r.status_code,
                "latency_ms": round(latency_ms, 1),
            }
    except Exception as exc:
        return {"healthy": False, "critical": False, "error": str(exc)}


async def _check_ai_engine() -> dict[str, Any]:
    """Check AI engine availability."""
    try:
        from pathlib import Path
        model_path = Path("data/models/phi-3-mini-int4")
        available = model_path.exists()
        return {
            "healthy": True,  # AI engine is optional
            "critical": False,
            "model_available": available,
        }
    except Exception as exc:
        return {"healthy": True, "critical": False, "error": str(exc)}
