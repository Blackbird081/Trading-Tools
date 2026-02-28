from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from interface.ws.manager import ConnectionManager

logger = logging.getLogger("ws.market")

router = APIRouter()
manager = ConnectionManager()


@router.websocket("/ws/market")
async def market_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time market data."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug("Received from client: %s", data)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
