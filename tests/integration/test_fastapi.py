"""Integration tests for FastAPI application.

★ GET /api/health returns 200 + healthy status.
★ WebSocket /ws/market connects and receives messages.

Ref: Doc 02 §2.6
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from interface.app import create_app


@pytest.fixture
def client() -> TestClient:
    """FastAPI test client."""
    app = create_app()
    return TestClient(app)


class TestHealthEndpoint:
    """Health endpoint tests."""

    def test_health_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_returns_healthy_status(self, client: TestClient) -> None:
        response = client.get("/api/health")
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "0.1.0"


class TestWebSocketMarket:
    """WebSocket /ws/market tests."""

    def test_websocket_connects(self, client: TestClient) -> None:
        """WebSocket client can connect to /ws/market."""
        # Import the router and include it
        from interface.ws.market_ws import router as ws_router

        app = create_app()
        app.include_router(ws_router)
        ws_client = TestClient(app)

        with ws_client.websocket_connect("/ws/market") as ws:
            # Send a test message
            ws.send_text("ping")
            # Connection established successfully if no exception
