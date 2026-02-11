from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from datetime import UTC, datetime

import httpx
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15

from adapters.ssi.credential_manager import SSICredentials

logger = logging.getLogger("ssi.auth")

SSI_AUTH_URL = "https://fc-tradeapi.ssi.com.vn/api/v2/Trading/AccessToken"
TOKEN_REFRESH_BUFFER_SECONDS = 300


class AuthenticationError(Exception):
    """Raised when SSI authentication fails. NEVER contains credentials."""


class TokenState:
    __slots__ = ("access_token", "expires_at", "issued_at")

    def __init__(self) -> None:
        self.access_token: str | None = None
        self.expires_at: float = 0.0
        self.issued_at: float = 0.0

    @property
    def is_valid(self) -> bool:
        return (
            self.access_token is not None
            and time.monotonic() < self.expires_at - TOKEN_REFRESH_BUFFER_SECONDS
        )

    @property
    def is_expired(self) -> bool:
        return time.monotonic() >= self.expires_at

    def update(self, token: str, expires_in: int) -> None:
        now = time.monotonic()
        self.access_token = token
        self.issued_at = now
        self.expires_at = now + expires_in


class SSIAuthClient:
    """RSA-signed authentication with SSI FastConnect API."""

    def __init__(
        self,
        credentials: SSICredentials,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._credentials = credentials
        self._http = http_client or httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            verify=True,
        )
        self._token = TokenState()
        self._refresh_lock = asyncio.Lock()

    async def get_access_token(self) -> str:
        if self._token.is_valid:
            assert self._token.access_token is not None
            return self._token.access_token
        async with self._refresh_lock:
            if self._token.is_valid:
                assert self._token.access_token is not None
                return self._token.access_token
            return await self._authenticate()

    async def _authenticate(self) -> str:
        timestamp = self._get_timestamp()
        payload = {
            "consumerID": self._credentials.consumer_id,
            "consumerSecret": self._credentials.consumer_secret,
            "timestamp": timestamp,
        }
        signature = self._sign_payload(payload)
        request_body = {**payload, "signature": signature}
        response = await self._http.post(
            SSI_AUTH_URL,
            json=request_body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        if response.status_code != 200:
            msg = f"SSI auth failed: HTTP {response.status_code}"
            raise AuthenticationError(msg)
        data = response.json()
        if data.get("status") != 200:
            msg = f"SSI auth rejected: {data.get('message', 'Unknown error')}"
            raise AuthenticationError(msg)
        access_token: str = data["data"]["accessToken"]
        expires_in: int = data["data"].get("expiresIn", 1800)
        self._token.update(access_token, expires_in)
        logger.info("SSI authentication successful. Token expires in %ds.", expires_in)
        return access_token

    def _sign_payload(self, payload: dict[str, str]) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        message_hash = SHA256.new(canonical.encode("utf-8"))
        signature_bytes = pkcs1_15.new(self._credentials.private_key).sign(message_hash)
        return base64.b64encode(signature_bytes).decode("ascii")

    @staticmethod
    def _get_timestamp() -> str:
        return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    async def close(self) -> None:
        await self._http.aclose()
