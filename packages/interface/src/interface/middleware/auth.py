"""Authentication middleware for sensitive API endpoints."""
from __future__ import annotations

import logging
import os
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

logger = logging.getLogger("interface.auth")

_PROTECTED_PREFIXES = ("/api/orders", "/api/safety", "/api/setup")
_DEV_ENVS = {"dev", "development", "test", "testing", "local"}


def _is_true(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _runtime_env() -> str:
    for name in ("APP_ENV", "ENVIRONMENT", "TRADING_ENV"):
        raw = os.getenv(name, "").strip().lower()
        if raw:
            return raw
    return "development"


def _auth_required() -> bool:
    explicit = os.getenv("API_AUTH_REQUIRED", "").strip()
    if explicit:
        return _is_true(explicit)
    return _runtime_env() not in _DEV_ENVS


def _extract_bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return ""


def _extract_token(request: Request) -> str:
    bearer = _extract_bearer_token(request)
    if bearer:
        return bearer
    return request.headers.get("X-API-Key", "").strip()


class AuthMiddleware(BaseHTTPMiddleware):
    """Protect sensitive endpoint groups in protected runtime mode."""

    def __init__(self, app: ASGIApp, protected_prefixes: tuple[str, ...] = _PROTECTED_PREFIXES) -> None:
        super().__init__(app)
        self._protected_prefixes = protected_prefixes

    def _is_protected_path(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in self._protected_prefixes)

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        if not _auth_required():
            return await call_next(request)

        path = request.url.path
        if not self._is_protected_path(path):
            return await call_next(request)

        expected = os.getenv("API_AUTH_TOKEN", "").strip()
        if not expected:
            logger.error("API auth is required but API_AUTH_TOKEN is missing")
            return JSONResponse(
                status_code=503,
                content={"detail": "API auth is required but API_AUTH_TOKEN is not configured."},
            )

        received = _extract_token(request)
        if not received or received != expected:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

        return await call_next(request)
