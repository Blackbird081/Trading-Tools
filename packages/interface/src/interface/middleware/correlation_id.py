from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from interface.observability import reset_correlation_id, set_correlation_id


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Attach one correlation id per request and return it in response headers."""

    async def dispatch(self, request: Request, call_next) -> Response:
        incoming = (
            request.headers.get("X-Correlation-ID")
            or request.headers.get("X-Request-ID")
            or str(uuid.uuid4())
        )
        token = set_correlation_id(incoming)
        request.state.correlation_id = incoming
        try:
            response = await call_next(request)
        finally:
            reset_correlation_id(token)
        response.headers["X-Correlation-ID"] = incoming
        return response

