"""ロガー設定 — structlog ベースの構造化ログ."""

from __future__ import annotations

import logging
from pathlib import Path

import structlog


def setup_logging(
    log_dir: Path,
    log_level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> structlog.BoundLogger:
    """structlog ベースのロガーを設定する.

    Args:
        log_dir: ログ出力ディレクトリ.
        log_level: ログレベル（DEBUG / INFO / WARNING / ERROR）.
        max_bytes: ログファイルの最大サイズ（バイト）.
        backup_count: ローテーション保持世代数.

    Returns:
        設定済みの structlog ロガー.
    """
    raise NotImplementedError


def get_logger(name: str) -> structlog.BoundLogger:
    """名前付きロガーを取得する.

    Args:
        name: ロガー名.

    Returns:
        structlog ロガーインスタンス.
    """
    logger: structlog.BoundLogger = structlog.get_logger(name)
    return logger


# 未使用 import を避けるために logging を参照
__all__ = ["setup_logging", "get_logger"]
_logging_module = logging
