from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, conversation_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[conversation_id].add(websocket)

    async def disconnect(self, conversation_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            connections = self._connections.get(conversation_id)
            if not connections:
                return
            connections.discard(websocket)
            if not connections:
                self._connections.pop(conversation_id, None)

    async def broadcast(self, conversation_id: int, payload: dict[str, Any]) -> None:
        async with self._lock:
            targets = list(self._connections.get(conversation_id, set()))
        stale: list[WebSocket] = []
        for websocket in targets:
            try:
                await websocket.send_json(payload)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            await self.disconnect(conversation_id, websocket)

    def connection_count(self, conversation_id: int) -> int:
        return len(self._connections.get(conversation_id, set()))


websocket_manager = WebSocketManager()
