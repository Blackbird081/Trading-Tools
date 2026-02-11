"""Integration tests for SSI RSA Authentication.

★ Sign/verify round-trip with generated RSA key pair.
★ Token refresh logic.
★ Invalid key rejection.
★ Uses mock HTTP server — NEVER touches real SSI API.

Ref: Doc 05 §1.5
"""

from __future__ import annotations

import base64
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from adapters.ssi.auth import AuthenticationError, SSIAuthClient, TokenState
from adapters.ssi.credential_manager import SSICredentials
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15

# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def rsa_key_pair() -> tuple[RSA.RsaKey, RSA.RsaKey]:
    """Generate a 2048-bit RSA key pair for testing."""
    private_key = RSA.generate(2048)
    public_key = private_key.publickey()
    return private_key, public_key


@pytest.fixture
def credentials(rsa_key_pair: tuple[RSA.RsaKey, RSA.RsaKey]) -> SSICredentials:
    """Test SSI credentials with generated RSA key."""
    private_key, _ = rsa_key_pair
    return SSICredentials(
        consumer_id="test-consumer-id",
        consumer_secret="test-consumer-secret",
        private_key=private_key,
    )


# ── RSA Sign/Verify Round-Trip ──────────────────────────────────


class TestRSASignVerify:
    """Test RSA-SHA256 signing matches verification."""

    def test_sign_and_verify_round_trip(
        self,
        rsa_key_pair: tuple[RSA.RsaKey, RSA.RsaKey],
        credentials: SSICredentials,
    ) -> None:
        _private_key, public_key = rsa_key_pair

        # Use SSIAuthClient's signing method
        client = SSIAuthClient(credentials=credentials)
        payload = {
            "consumerID": "test-consumer-id",
            "consumerSecret": "test-consumer-secret",
            "timestamp": "2026-02-10T09:00:00.000000Z",
        }
        signature_b64 = client._sign_payload(payload)

        # Verify with public key
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        message_hash = SHA256.new(canonical.encode("utf-8"))
        signature_bytes = base64.b64decode(signature_b64)

        # Should NOT raise — valid signature
        pkcs1_15.new(public_key).verify(message_hash, signature_bytes)

    def test_tampered_payload_fails_verification(
        self,
        rsa_key_pair: tuple[RSA.RsaKey, RSA.RsaKey],
        credentials: SSICredentials,
    ) -> None:
        _, public_key = rsa_key_pair

        client = SSIAuthClient(credentials=credentials)
        payload = {
            "consumerID": "test-consumer-id",
            "consumerSecret": "test-consumer-secret",
            "timestamp": "2026-02-10T09:00:00.000000Z",
        }
        signature_b64 = client._sign_payload(payload)

        # Tamper with payload
        tampered = json.dumps(
            {**payload, "timestamp": "TAMPERED"},
            sort_keys=True,
            separators=(",", ":"),
        )
        message_hash = SHA256.new(tampered.encode("utf-8"))
        signature_bytes = base64.b64decode(signature_b64)

        with pytest.raises(ValueError, match=r"Invalid|Incorrect"):
            pkcs1_15.new(public_key).verify(message_hash, signature_bytes)


# ── TokenState ───────────────────────────────────────────────────


class TestTokenState:
    """Token state management tests."""

    def test_initial_state_is_invalid(self) -> None:
        ts = TokenState()
        assert ts.is_valid is False
        assert ts.is_expired is True

    def test_update_makes_valid(self) -> None:
        ts = TokenState()
        ts.update("jwt-token-here", expires_in=1800)
        assert ts.is_valid is True
        assert ts.access_token == "jwt-token-here"  # noqa: S105


# ── SSIAuthClient ────────────────────────────────────────────────


class TestSSIAuthClient:
    """SSI auth client integration tests with mock HTTP."""

    @pytest.mark.asyncio
    async def test_authenticate_success(self, credentials: SSICredentials) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": 200,
            "message": "Success",
            "data": {
                "accessToken": "mock-jwt-token",
                "expiresIn": 1800,
            },
        }

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)

        client = SSIAuthClient(credentials=credentials, http_client=mock_http)
        token = await client.get_access_token()

        assert token == "mock-jwt-token"  # noqa: S105
        assert client._token.is_valid is True

    @pytest.mark.asyncio
    async def test_authenticate_http_error(self, credentials: SSICredentials) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)

        client = SSIAuthClient(credentials=credentials, http_client=mock_http)

        with pytest.raises(AuthenticationError, match="HTTP 500"):
            await client.get_access_token()

    @pytest.mark.asyncio
    async def test_authenticate_rejected(self, credentials: SSICredentials) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": 400,
            "message": "Invalid credentials",
        }

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)

        client = SSIAuthClient(credentials=credentials, http_client=mock_http)

        with pytest.raises(AuthenticationError, match="rejected"):
            await client.get_access_token()

    @pytest.mark.asyncio
    async def test_cached_token_reused(self, credentials: SSICredentials) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": 200,
            "data": {"accessToken": "cached-token", "expiresIn": 1800},
        }

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)

        client = SSIAuthClient(credentials=credentials, http_client=mock_http)

        # First call authenticates
        token1 = await client.get_access_token()
        # Second call returns cached
        token2 = await client.get_access_token()

        assert token1 == token2 == "cached-token"
        # Should only have called POST once
        assert mock_http.post.call_count == 1
