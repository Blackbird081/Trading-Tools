from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("ws.manager")


class ConnectionManager:
    """Manages active WebSocket connections for broadcasting.

    ★ Uses asyncio.Lock() to protect _connections set from concurrent access.
    ★ Uses a set instead of list for O(1) disconnect.
    """

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
        logger.info("WebSocket client connected. Total: %d", len(self._connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)
        logger.info("WebSocket client disconnected. Total: %d", len(self._connections))

    async def broadcast_json(self, data: dict[str, Any]) -> None:
        """Broadcast JSON data to all connected clients."""
        async with self._lock:
            snapshot = set(self._connections)

        disconnected: list[WebSocket] = []
        for ws in snapshot:
            try:
                await ws.send_json(data)
            except Exception:
                disconnected.append(ws)

        if disconnected:
            async with self._lock:
                for ws in disconnected:
                    self._connections.discard(ws)

    async def close_all(self) -> None:
        """Close all WebSocket connections gracefully (for shutdown)."""
        async with self._lock:
            snapshot = set(self._connections)
            self._connections.clear()

        for ws in snapshot:
            try:
                await ws.close(code=1001)  # 1001 = Going Away
            except Exception:
                pass

        logger.info("All WebSocket connections closed")

    @property
    def connection_count(self) -> int:
        return len(self._connections)


# ── Module-level singleton ────────────────────────────────────────────────────
# ★ Used by app.py for graceful shutdown
ws_manager = ConnectionManager()
