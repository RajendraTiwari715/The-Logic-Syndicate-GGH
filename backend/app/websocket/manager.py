from __future__ import annotations

import asyncio
import contextlib
import json
import threading

from fastapi import WebSocket


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        with self._lock:
            self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        with self._lock:
            self._connections.discard(websocket)

    async def broadcast(self, payload: dict) -> None:
        dead_connections: list[WebSocket] = []
        message = json.dumps(payload, default=str)
        with self._lock:
            sockets = list(self._connections)
        for connection in sockets:
            try:
                await connection.send_text(message)
            except Exception:
                dead_connections.append(connection)
        for connection in dead_connections:
            self.disconnect(connection)

    def broadcast_from_thread(self, payload: dict) -> None:
        if self._loop is None:
            return
        future = asyncio.run_coroutine_threadsafe(self.broadcast(payload), self._loop)
        with contextlib.suppress(Exception):
            future.result(timeout=2)
