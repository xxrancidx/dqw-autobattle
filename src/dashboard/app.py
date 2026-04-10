"""ダッシュボード — FastAPI アプリケーション（REST + WebSocket）."""

from __future__ import annotations

import asyncio
import base64
import logging
import queue
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import yaml
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from src.dashboard.ws import WebSocketManager
from src.logging.logger import get_ws_handler

logger = logging.getLogger(__name__)

CONFIG_PATH = Path("config.yaml")
STATIC_DIR = Path(__file__).parent / "static"

ws_manager = WebSocketManager()

# --------------------------------------------------------------------------- #
#  Application state (in-memory)
# --------------------------------------------------------------------------- #

_system_state: dict[str, Any] = {
    "running": False,
    "state": "IDLE",
    "battle_count": 0,
    "error_count": 0,
    "start_time": None,
}

_state_machine: Any = None  # Optional[StateMachine] — 実行時に注入
_system_task: asyncio.Task[None] | None = None
_log_task: asyncio.Task[None] | None = None
_preview_task: asyncio.Task[None] | None = None


def set_state_machine(machine: Any) -> None:
    """外部から StateMachine インスタンスを注入する."""
    global _state_machine  # noqa: PLW0603
    _state_machine = machine


def _uptime_seconds() -> float:
    """稼働時間（秒）を返す."""
    t = _system_state.get("start_time")
    if t is None or not _system_state["running"]:
        return 0.0
    return float(time.time() - t)


def _load_config() -> dict[str, Any]:
    """config.yaml を読み込む."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def _save_config(data: dict[str, Any]) -> None:
    """config.yaml に保存する."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False)


def _sync_state_from_machine() -> None:
    """StateMachine の状態を _system_state に同期する."""
    if _state_machine is not None:
        _system_state["running"] = _state_machine.is_running
        _system_state["state"] = _state_machine.state.name
        _system_state["battle_count"] = _state_machine.battle_count
        _system_state["error_count"] = _state_machine.error_count


# --------------------------------------------------------------------------- #
#  Background tasks: log queue → WS, preview → WS
# --------------------------------------------------------------------------- #


async def _log_queue_to_ws() -> None:
    """WebSocketLogHandler のキューからログを読み取り WS に配信する."""
    while True:
        handler = get_ws_handler()
        if handler is not None:
            try:
                while True:
                    entry = handler.log_queue.get_nowait()
                    await ws_manager.broadcast(entry, "logs")
            except queue.Empty:
                pass
        await asyncio.sleep(0.1)


async def _preview_to_ws() -> None:
    """StateMachine の最新キャプチャを定期的に WS に配信する."""
    while True:
        if _state_machine is not None and _state_machine.is_running:
            screen = _state_machine.last_screen
            if screen is not None:
                try:
                    _, buf = cv2.imencode(".png", screen)
                    b64 = base64.b64encode(np.asarray(buf).tobytes()).decode("ascii")
                    await ws_manager.broadcast({"type": "preview", "image": b64}, "preview")
                except Exception:
                    logger.debug("プレビュー配信エラー", exc_info=True)
        await asyncio.sleep(1.0)


# --------------------------------------------------------------------------- #
#  Lifespan
# --------------------------------------------------------------------------- #


@asynccontextmanager
async def _lifespan(application: FastAPI) -> AsyncIterator[None]:
    """アプリのライフサイクル管理."""
    global _log_task, _preview_task  # noqa: PLW0603
    _log_task = asyncio.create_task(_log_queue_to_ws())
    _preview_task = asyncio.create_task(_preview_to_ws())
    yield
    for task in (_log_task, _preview_task):
        if task is not None:
            task.cancel()


app = FastAPI(title="DQW AutoBattle Dashboard", lifespan=_lifespan)


# --------------------------------------------------------------------------- #
#  REST endpoints
# --------------------------------------------------------------------------- #


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """ダッシュボード UI を返す."""
    html_path = STATIC_DIR / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.post("/api/start")
async def start_system() -> dict[str, str]:
    """システムを開始する."""
    global _system_task  # noqa: PLW0603

    if _state_machine is not None:
        # 実 StateMachine モード
        if _state_machine.is_running:
            return {"status": "already_running"}
        _system_state["start_time"] = time.time()

        async def _run_machine() -> None:
            try:
                await _state_machine.start()
            except Exception:
                logger.exception("StateMachine 異常終了")
            finally:
                _sync_state_from_machine()

        _system_task = asyncio.create_task(_run_machine())
        _system_state["running"] = True
        _system_state["state"] = "SEARCHING"
        logger.info("システム開始")
        await ws_manager.broadcast({"type": "state", "state": "SEARCHING"}, "state")
        return {"status": "started"}

    # StateMachine 未注入時（テスト互換モード）
    if _system_state["running"]:
        return {"status": "already_running"}
    _system_state["running"] = True
    _system_state["state"] = "SEARCHING"
    _system_state["start_time"] = time.time()
    logger.info("システム開始")
    await ws_manager.broadcast({"type": "state", "state": "SEARCHING"}, "state")
    return {"status": "started"}


@app.post("/api/stop")
async def stop_system() -> dict[str, str]:
    """システムを停止する."""
    if _state_machine is not None:
        # 実 StateMachine モード
        if not _state_machine.is_running and not _system_state["running"]:
            return {"status": "already_stopped"}
        await _state_machine.stop()
        _system_state["running"] = False
        _system_state["state"] = "IDLE"
        _system_state["start_time"] = None
        logger.info("システム停止")
        await ws_manager.broadcast({"type": "state", "state": "IDLE"}, "state")
        return {"status": "stopped"}

    # テスト互換モード
    if not _system_state["running"]:
        return {"status": "already_stopped"}
    _system_state["running"] = False
    _system_state["state"] = "IDLE"
    _system_state["start_time"] = None
    logger.info("システム停止")
    await ws_manager.broadcast({"type": "state", "state": "IDLE"}, "state")
    return {"status": "stopped"}


@app.get("/api/status")
async def get_status() -> dict[str, Any]:
    """現在のシステム状態を返す."""
    _sync_state_from_machine()
    return {
        "running": _system_state["running"],
        "state": _system_state["state"],
        "battle_count": _system_state["battle_count"],
        "error_count": _system_state["error_count"],
        "uptime_seconds": _uptime_seconds(),
    }


@app.get("/api/config")
async def get_config() -> dict[str, Any]:
    """現在の設定値を返す."""
    return _load_config()


@app.put("/api/config")
async def update_config(body: dict[str, Any]) -> dict[str, str]:
    """設定値を動的に更新する."""
    cfg = _load_config()
    cfg.update(body)
    _save_config(cfg)
    logger.info("設定更新: %s", list(body.keys()))
    return {"status": "updated"}


# --------------------------------------------------------------------------- #
#  WebSocket endpoints
# --------------------------------------------------------------------------- #


@app.websocket("/ws/logs")
async def ws_logs(websocket: WebSocket) -> None:
    """リアルタイムログストリーム."""
    await ws_manager.connect(websocket, "logs")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, "logs")


@app.websocket("/ws/state")
async def ws_state(websocket: WebSocket) -> None:
    """状態遷移イベント."""
    await ws_manager.connect(websocket, "state")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, "state")


@app.websocket("/ws/preview")
async def ws_preview(websocket: WebSocket) -> None:
    """最新キャプチャ画像（Base64）."""
    await ws_manager.connect(websocket, "preview")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, "preview")
