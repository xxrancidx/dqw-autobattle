"""ロガー設定のテスト."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.logging.logger import get_logger, setup_logging


class TestLogger:
    """ロガー設定のテスト."""

    def test_setup_logging_not_implemented(self, tmp_path: Path) -> None:
        """setup_logging() が NotImplementedError を送出する."""
        with pytest.raises(NotImplementedError):
            setup_logging(log_dir=tmp_path)

    def test_get_logger(self) -> None:
        """get_logger() がロガーインスタンスを返す."""
        logger = get_logger("test")
        assert logger is not None
