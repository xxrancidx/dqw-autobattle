"""ロガー設定のテスト."""

from __future__ import annotations

import logging
from pathlib import Path

from src.logging.logger import WebSocketLogHandler, get_logger, get_ws_handler, setup_logging


class TestLogger:
    """ロガー設定のテスト."""

    def test_setup_logging_returns_logger(self, tmp_path: Path) -> None:
        """setup_logging() が structlog ロガーを返す."""
        logger = setup_logging(log_dir=tmp_path)
        assert logger is not None

    def test_setup_logging_creates_log_file(self, tmp_path: Path) -> None:
        """setup_logging() がログファイルを作成する."""
        setup_logging(log_dir=tmp_path)
        assert (tmp_path / "app.log").exists()

    def test_setup_logging_configures_root_handlers(self, tmp_path: Path) -> None:
        """setup_logging() がルートロガーにハンドラを設定する."""
        setup_logging(log_dir=tmp_path)
        root = logging.getLogger()
        assert len(root.handlers) >= 3  # file + console + ws

    def test_ws_handler_singleton(self, tmp_path: Path) -> None:
        """setup_logging() 後に get_ws_handler() がハンドラを返す."""
        setup_logging(log_dir=tmp_path)
        handler = get_ws_handler()
        assert handler is not None
        assert isinstance(handler, WebSocketLogHandler)

    def test_ws_handler_queue_receives_logs(self, tmp_path: Path) -> None:
        """WebSocketLogHandler のキューにログが蓄積される."""
        setup_logging(log_dir=tmp_path)
        handler = get_ws_handler()
        assert handler is not None

        # setup_logging 内のログを消費
        while not handler.log_queue.empty():
            handler.log_queue.get_nowait()

        test_logger = logging.getLogger("test_ws_queue")
        test_logger.info("テストメッセージ")

        # キューにエントリがあるはず
        assert not handler.log_queue.empty()
        entry = handler.log_queue.get_nowait()
        assert entry["type"] == "log"
        assert "テストメッセージ" in entry["message"]

    def test_get_logger(self) -> None:
        """get_logger() がロガーインスタンスを返す."""
        logger = get_logger("test")
        assert logger is not None
