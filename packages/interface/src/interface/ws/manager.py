from __future__ import annotations

import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("ws.manager")


class ConnectionManager:
    """Manages active WebSocket connections for broadcasting."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)
        logger.info("WebSocket client connected. Total: %d", len(self._connections))

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.remove(websocket)
        logger.info("WebSocket client disconnected. Total: %d", len(self._connections))

    async def broadcast_json(self, data: dict[str, Any]) -> None:
        """Broadcast JSON data to all connected clients."""
        disconnected: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_json(data)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self._connections.remove(ws)

    @property
    def connection_count(self) -> int:
        return len(self._connections)
