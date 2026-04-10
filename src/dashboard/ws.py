"""WebSocket マネージャ — クライアント接続の管理とブロードキャスト."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


class WebSocketManager:
    """WebSocket 接続を管理し、メッセージをブロードキャストする.

    チャネル別に接続を管理する。チャネル例: "logs", "state", "preview"
    """

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}

    @property
    def connection_count(self) -> int:
        """全チャネルの合計接続数."""
        return sum(len(v) for v in self._connections.values())

    def connections(self, channel: str) -> list[WebSocket]:
        """指定チャネルの接続リストを返す."""
        return self._connections.get(channel, [])

    async def connect(self, websocket: WebSocket, channel: str = "default") -> None:
        """新しい WebSocket 接続を受け入れる.

        Args:
            websocket: 接続する WebSocket インスタンス.
            channel: 接続先チャネル名.
        """
        await websocket.accept()
        self._connections.setdefault(channel, []).append(websocket)
        logger.info("WebSocket 接続: channel=%s (total=%d)", channel, self.connection_count)

    async def disconnect(self, websocket: WebSocket, channel: str = "default") -> None:
        """WebSocket 接続を切断する.

        Args:
            websocket: 切断する WebSocket インスタンス.
            channel: チャネル名.
        """
        conns = self._connections.get(channel, [])
        if websocket in conns:
            conns.remove(websocket)
        logger.info("WebSocket 切断: channel=%s (total=%d)", channel, self.connection_count)

    async def broadcast(self, message: dict[str, Any], channel: str = "default") -> None:
        """指定チャネルの全クライアントにメッセージを送信する.

        Args:
            message: 送信する JSON シリアライズ可能な辞書.
            channel: 送信先チャネル名.
        """
        conns = self._connections.get(channel, [])
        disconnected: list[WebSocket] = []
        for ws in conns:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_json(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            conns.remove(ws)

    async def broadcast_all(self, message: dict[str, Any]) -> None:
        """全チャネルにメッセージを送信する."""
        for channel in list(self._connections):
            await self.broadcast(message, channel)
