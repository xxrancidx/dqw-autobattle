"""WebSocket マネージャ — クライアント接続の管理とブロードキャスト."""

from __future__ import annotations

from typing import Any

from fastapi import WebSocket


class WebSocketManager:
    """WebSocket 接続を管理し、メッセージをブロードキャストする."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """新しい WebSocket 接続を受け入れる.

        Args:
            websocket: 接続する WebSocket インスタンス.
        """
        raise NotImplementedError

    async def disconnect(self, websocket: WebSocket) -> None:
        """WebSocket 接続を切断する.

        Args:
            websocket: 切断する WebSocket インスタンス.
        """
        raise NotImplementedError

    async def broadcast(self, message: dict[str, Any]) -> None:
        """全接続クライアントにメッセージを送信する.

        Args:
            message: 送信する JSON シリアライズ可能な辞書.
        """
        raise NotImplementedError
