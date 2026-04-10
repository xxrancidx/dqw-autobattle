"""ダッシュボードのテスト."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.dashboard.app import app
from src.dashboard.ws import WebSocketManager


class TestWebSocketManager:
    """WebSocketManager のテスト."""

    def test_init(self) -> None:
        """初期化時に接続リストが空であること."""
        manager = WebSocketManager()
        assert manager._connections == []


class TestDashboardAPI:
    """ダッシュボード REST API のテスト."""

    def test_status_endpoint_exists(self) -> None:
        """GET /api/status エンドポイントが存在する."""
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/status")
        # NotImplementedError → 500 が期待される（スケルトン段階）
        assert response.status_code == 500

    def test_start_endpoint_exists(self) -> None:
        """POST /api/start エンドポイントが存在する."""
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/api/start")
        assert response.status_code == 500

    def test_stop_endpoint_exists(self) -> None:
        """POST /api/stop エンドポイントが存在する."""
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/api/stop")
        assert response.status_code == 500
