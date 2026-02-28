"""SSI Request Signer — HMAC-SHA256 request signing for SSI FastConnect API.

★ SEC-01: All SSI API requests must be signed with HMAC-SHA256.
★ Signature = HMAC-SHA256(secret_key, timestamp + method + path + body_hash)
★ Prevents replay attacks with timestamp validation (±30s window).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any

logger = logging.getLogger("ssi.signer")

# Maximum age of a signed request (seconds)
MAX_REQUEST_AGE_SECONDS = 30


class SSIRequestSigner:
    """Signs SSI API requests with HMAC-SHA256.

    ★ Inspired by SSI FastConnect API v2 authentication spec.
    ★ Signature prevents MITM and replay attacks.
    """

    def __init__(self, consumer_id: str, consumer_secret: str) -> None:
        self._consumer_id = consumer_id
        self._consumer_secret = consumer_secret.encode("utf-8")

    def sign_request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        timestamp: int | None = None,
    ) -> dict[str, str]:
        """Generate signed headers for an SSI API request.

        Returns headers dict with:
        - X-Consumer-ID: consumer identifier
        - X-Timestamp: Unix timestamp (seconds)
        - X-Signature: HMAC-SHA256 signature
        """
        ts = timestamp or int(time.time())

        # Canonical body: sorted JSON or empty string
        if body:
            body_str = json.dumps(body, sort_keys=True, separators=(",", ":"))
        else:
            body_str = ""

        # Body hash (SHA256 hex)
        body_hash = hashlib.sha256(body_str.encode("utf-8")).hexdigest()

        # Message to sign: timestamp + method + path + body_hash
        message = f"{ts}\n{method.upper()}\n{path}\n{body_hash}"

        # HMAC-SHA256 signature
        signature = hmac.new(
            self._consumer_secret,
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        logger.debug("Signed request: method=%s path=%s ts=%d", method, path, ts)

        return {
            "X-Consumer-ID": self._consumer_id,
            "X-Timestamp": str(ts),
            "X-Signature": signature,
        }

    def verify_signature(
        self,
        method: str,
        path: str,
        timestamp: int,
        signature: str,
        body: dict[str, Any] | None = None,
    ) -> bool:
        """Verify a request signature (for webhook callbacks).

        Also validates timestamp is within MAX_REQUEST_AGE_SECONDS.
        """
        # Check timestamp freshness
        now = int(time.time())
        if abs(now - timestamp) > MAX_REQUEST_AGE_SECONDS:
            logger.warning(
                "Request timestamp too old: ts=%d, now=%d, diff=%ds",
                timestamp, now, abs(now - timestamp),
            )
            return False

        # Recompute expected signature
        expected_headers = self.sign_request(method, path, body, timestamp=timestamp)
        expected_sig = expected_headers["X-Signature"]

        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(signature, expected_sig)
