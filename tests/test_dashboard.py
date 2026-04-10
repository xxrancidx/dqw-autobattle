"""ダッシュボードのテスト."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketState

import src.dashboard.app as app_mod
from src.dashboard.app import _system_state, app
from src.dashboard.ws import WebSocketManager

# --------------------------------------------------------------------------- #
#  Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture(autouse=True)
def _reset_state():
    """各テスト前にシステム状態をリセットする."""
    _system_state["running"] = False
    _system_state["state"] = "IDLE"
    _system_state["battle_count"] = 0
    _system_state["error_count"] = 0
    _system_state["start_time"] = None
    app_mod._state_machine = None
    yield


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


# --------------------------------------------------------------------------- #
#  WebSocketManager unit tests
# --------------------------------------------------------------------------- #


class TestWebSocketManager:
    """WebSocketManager のユニットテスト."""

    def test_init_empty(self) -> None:
        """初期化時に接続数が 0."""
        mgr = WebSocketManager()
        assert mgr.connection_count == 0

    def test_connections_empty_channel(self) -> None:
        """存在しないチャネルは空リスト."""
        mgr = WebSocketManager()
        assert mgr.connections("nonexistent") == []

    @pytest.mark.asyncio()
    async def test_connect_and_disconnect(self) -> None:
        """connect / disconnect で接続数が増減する."""
        mgr = WebSocketManager()
        ws = AsyncMock()
        await mgr.connect(ws, "test")
        assert mgr.connection_count == 1
        assert len(mgr.connections("test")) == 1
        await mgr.disconnect(ws, "test")
        assert mgr.connection_count == 0

    @pytest.mark.asyncio()
    async def test_broadcast_sends_json(self) -> None:
        """broadcast が接続中のクライアントに JSON を送信する."""
        mgr = WebSocketManager()
        ws = AsyncMock()
        ws.client_state = WebSocketState.CONNECTED
        await mgr.connect(ws, "ch")
        await mgr.broadcast({"hello": "world"}, "ch")
        ws.send_json.assert_called_once_with({"hello": "world"})

    @pytest.mark.asyncio()
    async def test_broadcast_removes_failed(self) -> None:
        """送信失敗した接続は自動除去される."""
        mgr = WebSocketManager()
        ws = AsyncMock()
        ws.client_state = WebSocketState.CONNECTED
        ws.send_json.side_effect = RuntimeError("closed")
        await mgr.connect(ws, "ch")
        await mgr.broadcast({"x": 1}, "ch")
        assert mgr.connection_count == 0

    @pytest.mark.asyncio()
    async def test_broadcast_all(self) -> None:
        """broadcast_all が全チャネルに送信する."""
        mgr = WebSocketManager()
        ws1 = AsyncMock()
        ws1.client_state = WebSocketState.CONNECTED
        ws2 = AsyncMock()
        ws2.client_state = WebSocketState.CONNECTED
        await mgr.connect(ws1, "a")
        await mgr.connect(ws2, "b")
        await mgr.broadcast_all({"msg": "hi"})
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()


# --------------------------------------------------------------------------- #
#  REST API tests
# --------------------------------------------------------------------------- #


class TestDashboardIndex:
    """GET / のテスト."""

    def test_index_returns_html(self, client: TestClient) -> None:
        """GET / が HTML を返す."""
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "DQW AutoBattle Dashboard" in resp.text


class TestStatusEndpoint:
    """GET /api/status のテスト."""

    def test_status_idle(self, client: TestClient) -> None:
        """初期状態で IDLE."""
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["running"] is False
        assert data["state"] == "IDLE"
        assert data["battle_count"] == 0
        assert data["error_count"] == 0
        assert data["uptime_seconds"] == 0.0


class TestStartStopEndpoints:
    """POST /api/start, /api/stop のテスト."""

    def test_start(self, client: TestClient) -> None:
        """start でシステムが起動する."""
        resp = client.post("/api/start")
        assert resp.status_code == 200
        assert resp.json()["status"] == "started"
        # status 確認
        status = client.get("/api/status").json()
        assert status["running"] is True
        assert status["state"] == "SEARCHING"

    def test_start_already_running(self, client: TestClient) -> None:
        """二重起動は already_running."""
        client.post("/api/start")
        resp = client.post("/api/start")
        assert resp.json()["status"] == "already_running"

    def test_stop(self, client: TestClient) -> None:
        """stop でシステムが停止する."""
        client.post("/api/start")
        resp = client.post("/api/stop")
        assert resp.status_code == 200
        assert resp.json()["status"] == "stopped"
        status = client.get("/api/status").json()
        assert status["running"] is False
        assert status["state"] == "IDLE"

    def test_stop_already_stopped(self, client: TestClient) -> None:
        """既に停止中なら already_stopped."""
        resp = client.post("/api/stop")
        assert resp.json()["status"] == "already_stopped"


class TestConfigEndpoints:
    """GET/PUT /api/config のテスト."""

    def test_get_config(self, client: TestClient) -> None:
        """GET /api/config が辞書を返す."""
        resp = client.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_put_config(self, client: TestClient, tmp_path, monkeypatch) -> None:
        """PUT /api/config で設定を更新できる."""
        import src.dashboard.app as app_mod

        tmp_cfg = tmp_path / "config.yaml"
        tmp_cfg.write_text("engine:\n  max_scroll_retry: 10\n", encoding="utf-8")
        monkeypatch.setattr(app_mod, "CONFIG_PATH", tmp_cfg)

        resp = client.put(
            "/api/config",
            json={"engine": {"max_scroll_retry": 20}},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "updated"

        # 反映確認
        cfg = client.get("/api/config").json()
        assert cfg["engine"]["max_scroll_retry"] == 20


# --------------------------------------------------------------------------- #
#  WebSocket endpoint tests
# --------------------------------------------------------------------------- #


class TestWebSocketEndpoints:
    """WebSocket エンドポイントの接続テスト."""

    def test_ws_logs_connect(self, client: TestClient) -> None:
        """ws/logs に接続できる."""
        with client.websocket_connect("/ws/logs"):
            pass  # connect/disconnect succeeds

    def test_ws_state_connect(self, client: TestClient) -> None:
        """ws/state に接続できる."""
        with client.websocket_connect("/ws/state"):
            pass

    def test_ws_preview_connect(self, client: TestClient) -> None:
        """ws/preview に接続できる."""
        with client.websocket_connect("/ws/preview"):
            pass
