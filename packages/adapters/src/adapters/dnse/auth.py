from __future__ import annotations

import logging
import time

import httpx

logger = logging.getLogger("dnse.auth")

DNSE_AUTH_URL = "https://auth-api.dnse.com.vn/api/auth/login"


class DNSEAuthClient:
    """DNSE Entrade X authentication — JWT + Refresh Token.

    Stub for Phase 2. Full implementation when DNSE integration is needed.
    """

    def __init__(
        self,
        username: str = "",
        password: str = "",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._username = username
        self._password = password
        self._http = http_client or httpx.AsyncClient(timeout=10.0)
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._token_expires_at: float = 0.0

    async def get_access_token(self) -> str:
        """Get valid access token, refreshing if needed."""
        if self._access_token and time.monotonic() < self._token_expires_at - 60:
            return self._access_token
        msg = "DNSE authentication not yet implemented (Phase 5)"
        raise NotImplementedError(msg)

    async def close(self) -> None:
        await self._http.aclose()
