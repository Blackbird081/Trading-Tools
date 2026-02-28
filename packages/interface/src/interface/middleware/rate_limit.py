"""Rate limiting middleware — token bucket algorithm with IP eviction."""
from __future__ import annotations
import ipaddress
import logging
import time
from typing import Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

logger = logging.getLogger("interface.rate_limit")
_EXEMPT_PATHS = {"/api/health", "/api/health/live", "/api/health/ready"}
_IP_EVICTION_IDLE_SECONDS = 3600.0

# ★ FIX: Only trust X-Forwarded-For from these trusted proxy networks
_TRUSTED_PROXY_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),       # Private class A
    ipaddress.ip_network("172.16.0.0/12"),     # Private class B
    ipaddress.ip_network("192.168.0.0/16"),    # Private class C
    ipaddress.ip_network("127.0.0.0/8"),       # Loopback (local dev)
]


def _is_trusted_proxy(host: str) -> bool:
    """Check if the direct client IP is a trusted proxy."""
    try:
        addr = ipaddress.ip_address(host)
        return any(addr in network for network in _TRUSTED_PROXY_NETWORKS)
    except ValueError:
        return False


def _get_client_ip(request: Request) -> str:
    """Get real client IP, only trusting X-Forwarded-For from trusted proxies.

    ★ FIX: Prevents X-Forwarded-For spoofing by untrusted clients.
    """
    direct_host = request.client.host if request.client else "unknown"
    if _is_trusted_proxy(direct_host):
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return direct_host


class TokenBucket:
    __slots__ = ("capacity", "rate", "tokens", "last_refill")

    def __init__(self, capacity: float, rate: float) -> None:
        self.capacity = capacity
        self.rate = rate
        self.tokens = capacity
        self.last_refill = time.monotonic()

    def consume(self, tokens: float = 1.0) -> bool:
        now = time.monotonic()
        self.tokens = min(self.capacity, self.tokens + (now - self.last_refill) * self.rate)
        self.last_refill = now
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    @property
    def retry_after(self) -> float:
        return 0.0 if self.tokens >= 1.0 else (1.0 - self.tokens) / self.rate


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP rate limiting with token bucket + memory-bounded eviction."""

    def __init__(self, app: ASGIApp, requests_per_minute: int = 60, order_requests_per_minute: int = 10) -> None:
        super().__init__(app)
        self._default_rate = requests_per_minute / 60.0
        self._order_rate = order_requests_per_minute / 60.0
        self._default_capacity = float(requests_per_minute)
        self._order_capacity = float(order_requests_per_minute)
        self._buckets: dict[str, TokenBucket] = {}
        self._order_buckets: dict[str, TokenBucket] = {}
        self._last_seen: dict[str, float] = {}
        self._request_count = 0

    def _get_bucket(self, ip: str, is_order: bool) -> TokenBucket:
        now = time.monotonic()
        self._last_seen[ip] = now
        self._request_count += 1
        if self._request_count % 1000 == 0:
            cutoff = now - _IP_EVICTION_IDLE_SECONDS
            for k in [k for k, v in self._last_seen.items() if v < cutoff]:
                self._buckets.pop(k, None)
                self._order_buckets.pop(k, None)
                self._last_seen.pop(k, None)
        buckets = self._order_buckets if is_order else self._buckets
        if ip not in buckets:
            buckets[ip] = TokenBucket(self._order_capacity if is_order else self._default_capacity, self._order_rate if is_order else self._default_rate)
        return buckets[ip]

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        path = request.url.path
        if path in _EXEMPT_PATHS:
            return await call_next(request)
        # ★ FIX: Use trusted-proxy-aware IP resolution to prevent spoofing
        client_ip = _get_client_ip(request)
        bucket = self._get_bucket(client_ip, "/orders" in path or "/portfolio" in path)
        if not bucket.consume():
            retry_after = bucket.retry_after
            return JSONResponse(status_code=429, content={"error": "Too Many Requests", "retry_after": retry_after}, headers={"Retry-After": str(int(retry_after) + 1)})
        return await call_next(request)
