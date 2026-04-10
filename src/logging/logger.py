"""ロガー設定 — structlog ベースの構造化ログ."""

from __future__ import annotations

import contextlib
import logging
import logging.handlers
import queue
from pathlib import Path
from typing import Any

import structlog


class WebSocketLogHandler(logging.Handler):
    """ログレコードをキューに蓄積し、WebSocket 配信用に提供するハンドラ.

    非同期の WebSocket broadcast を同期ログハンドラから安全に呼ぶため、
    キューを介してメッセージを受け渡す。
    """

    def __init__(self) -> None:
        super().__init__()
        self._queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=1000)

    @property
    def log_queue(self) -> queue.Queue[dict[str, Any]]:
        """ログメッセージキュー."""
        return self._queue

    def emit(self, record: logging.LogRecord) -> None:
        """ログレコードをキューに追加する."""
        try:
            msg = self.format(record)
            entry: dict[str, Any] = {
                "type": "log",
                "level": record.levelname,
                "message": msg,
                "logger": record.name,
                "timestamp": record.created,
            }
            try:
                self._queue.put_nowait(entry)
            except queue.Full:
                # キューが満杯なら古いエントリを捨てて追加
                with contextlib.suppress(queue.Empty):
                    self._queue.get_nowait()
                self._queue.put_nowait(entry)
        except Exception:
            self.handleError(record)


# モジュールレベルで保持するシングルトン
_ws_handler: WebSocketLogHandler | None = None


def get_ws_handler() -> WebSocketLogHandler | None:
    """WebSocket ログハンドラのシングルトンを返す."""
    return _ws_handler


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
    global _ws_handler  # noqa: PLW0603

    log_dir.mkdir(parents=True, exist_ok=True)

    # ファイルハンドラ（ローテーション付き）
    file_handler = logging.handlers.RotatingFileHandler(
        filename=str(log_dir / "app.log"),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)

    # コンソールハンドラ
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # WebSocket ハンドラ
    _ws_handler = WebSocketLogHandler()
    _ws_handler.setLevel(logging.INFO)

    # フォーマッタ
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    _ws_handler.setFormatter(formatter)

    # ルートロガー設定
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    # 既存ハンドラをクリアして重複防止
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(_ws_handler)

    # structlog の設定
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logger: structlog.BoundLogger = structlog.get_logger("dqw")
    logger.info("ロガー初期化完了", log_dir=str(log_dir), level=log_level)
    return logger


def get_logger(name: str) -> structlog.BoundLogger:
    """名前付きロガーを取得する.

    Args:
        name: ロガー名.

    Returns:
        structlog ロガーインスタンス.
    """
    logger: structlog.BoundLogger = structlog.get_logger(name)
    return logger
