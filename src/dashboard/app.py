"""ダッシュボード — FastAPI アプリケーション（REST + WebSocket）."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from src.dashboard.ws import WebSocketManager

app = FastAPI(title="DQW AutoBattle Dashboard")
ws_manager = WebSocketManager()

app.mount(
    "/static",
    StaticFiles(directory="src/dashboard/static"),
    name="static",
)


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """ダッシュボード UI を返す."""
    raise NotImplementedError


@app.get("/api/status")
async def get_status() -> dict[str, Any]:
    """現在のシステム状態を返す.

    Returns:
        状態情報を含む辞書.
    """
    raise NotImplementedError


@app.post("/api/start")
async def start_system() -> dict[str, str]:
    """システムを開始する.

    Returns:
        結果メッセージ.
    """
    raise NotImplementedError


@app.post("/api/stop")
async def stop_system() -> dict[str, str]:
    """システムを停止する.

    Returns:
        結果メッセージ.
    """
    raise NotImplementedError


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket エンドポイント — リアルタイムログストリーム.

    Args:
        websocket: WebSocket 接続.
    """
    raise NotImplementedError
