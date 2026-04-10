"""エントリポイント — 各コンポーネントの初期化と起動."""

from __future__ import annotations

import asyncio
import logging
import signal
import threading
from pathlib import Path
from typing import Any

import uvicorn
import yaml

from src.capture.screen import ScreenCapture
from src.control.adb import AdbController
from src.dashboard.app import app, set_state_machine, ws_manager
from src.engine.state_machine import StateMachine
from src.logging.logger import setup_logging
from src.recognition.detector import StateDetector
from src.recognition.matcher import TemplateMatcher

logger = logging.getLogger(__name__)


def load_config(config_path: Path) -> dict[str, Any]:
    """設定ファイルを読み込む.

    Args:
        config_path: config.yaml のパス.

    Returns:
        設定値の辞書.
    """
    with open(config_path, encoding="utf-8") as f:
        config: dict[str, Any] = yaml.safe_load(f)
    return config


def _save_error_screenshot(screen: Any, screenshot_dir: Path, max_count: int) -> None:
    """エラー時のスクリーンショットを保存する.

    Args:
        screen: numpy 配列の画面キャプチャ.
        screenshot_dir: 保存先ディレクトリ.
        max_count: 保持する最大枚数.
    """
    import cv2

    screenshot_dir.mkdir(parents=True, exist_ok=True)

    # タイムスタンプ付きファイル名
    import datetime

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = screenshot_dir / f"error_{ts}.png"
    cv2.imwrite(str(path), screen)
    logger.info("エラースクリーンショット保存: %s", path)

    # 古いファイルを削除して max_count 枚以内に
    files = sorted(screenshot_dir.glob("error_*.png"), key=lambda p: p.stat().st_mtime)
    while len(files) > max_count:
        oldest = files.pop(0)
        oldest.unlink()
        logger.debug("古いスクリーンショット削除: %s", oldest)


def _start_dashboard_server(host: str, port: int) -> None:
    """ダッシュボードサーバーを別スレッドで起動する.

    Args:
        host: バインドホスト.
        port: バインドポート.
    """
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    server.run()


async def main() -> None:
    """アプリケーションのメインエントリポイント."""
    config_path = Path("config.yaml")
    config = load_config(config_path)

    # ロガー設定
    logging_conf = config.get("logging", {})
    assert isinstance(logging_conf, dict)
    log_dir = Path(str(logging_conf.get("file", "logs/app.log"))).parent
    setup_logging(
        log_dir=log_dir,
        log_level=str(logging_conf.get("level", "INFO")),
        max_bytes=int(logging_conf.get("max_bytes", 10 * 1024 * 1024)),
        backup_count=int(logging_conf.get("backup_count", 5)),
    )

    logger.info("=== DQW AutoBattle System 起動 ===")

    # ---------- コンポーネント初期化 ----------

    # デバイスシリアル
    device_conf = config.get("device", {})
    assert isinstance(device_conf, dict)
    device_serial = device_conf.get("serial")

    # AdbController
    control_conf = config.get("control", {})
    assert isinstance(control_conf, dict)
    controller = AdbController(
        device_serial=str(device_serial) if device_serial else None,
        cooldown=float(control_conf.get("tap_cooldown_ms", 300)) / 1000.0,
    )

    # ScreenCapture
    capture_conf = config.get("capture", {})
    assert isinstance(capture_conf, dict)
    capture = ScreenCapture(
        device_serial=str(device_serial) if device_serial else None,
        max_retries=int(capture_conf.get("retry_count", 3)),
        retry_delay=float(capture_conf.get("retry_delay", 0.5)),
    )

    # TemplateMatcher
    recognition_conf = config.get("recognition", {})
    assert isinstance(recognition_conf, dict)
    templates_dir = Path(str(recognition_conf.get("template_dir", "templates/")))
    matcher = TemplateMatcher(
        templates_dir=templates_dir,
        threshold=float(recognition_conf.get("threshold", 0.8)),
    )
    if templates_dir.exists():
        matcher.load_templates()
    else:
        logger.warning("テンプレートディレクトリが見つかりません: %s", templates_dir)

    # StateDetector
    detector = StateDetector(matcher=matcher)

    # StateMachine
    engine_conf = config.get("engine", {})
    assert isinstance(engine_conf, dict)
    scroll_conf = control_conf.get("scroll", {})
    assert isinstance(scroll_conf, dict)

    machine = StateMachine(
        capture=capture,
        detector=detector,
        controller=controller,
        max_scroll_retry=int(engine_conf.get("max_scroll_retry", 10)),
        dialog_retry_count=int(engine_conf.get("dialog_retry_count", 3)),
        max_runtime_minutes=int(engine_conf.get("max_runtime_minutes", 60)),
        tick_interval=float(capture_conf.get("interval_ms", 500)) / 1000.0,
        scroll_duration_ms=int(scroll_conf.get("duration_ms", 2000)),
    )

    # エラースクリーンショット設定
    screenshot_dir = Path(str(logging_conf.get("screenshot_dir", "logs/screenshots/")))
    screenshot_max = int(logging_conf.get("screenshot_max_count", 100))

    # StateMachine のイベントコールバック — WS 配信 + エラースクリーンショット
    async def on_machine_event(event_type: str, data: dict[str, Any]) -> None:
        if event_type == "status":
            await ws_manager.broadcast({"type": "state", **data}, "state")
            # ERROR 遷移時にスクリーンショット保存
            if data.get("state") == "ERROR":
                screen = machine.last_screen
                if screen is not None:
                    _save_error_screenshot(screen, screenshot_dir, screenshot_max)

    machine.add_event_callback(on_machine_event)

    # ダッシュボードに StateMachine を注入
    set_state_machine(machine)

    # ---------- ダッシュボードサーバー起動 ----------

    dashboard_conf = config.get("dashboard", {})
    assert isinstance(dashboard_conf, dict)
    host = str(dashboard_conf.get("host", "127.0.0.1"))
    port = int(dashboard_conf.get("port", 8080))

    server_thread = threading.Thread(
        target=_start_dashboard_server,
        args=(host, port),
        daemon=True,
    )
    server_thread.start()
    logger.info("ダッシュボード起動: http://%s:%d", host, port)

    # ---------- グレースフルシャットダウン ----------

    shutdown_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("シャットダウンシグナル受信")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    # Windows では loop.add_signal_handler が使えないため try/except
    try:
        loop.add_signal_handler(signal.SIGINT, _signal_handler)
        loop.add_signal_handler(signal.SIGTERM, _signal_handler)
    except NotImplementedError:
        # Windows: signal モジュールで代替
        signal.signal(signal.SIGINT, lambda s, f: _signal_handler())
        signal.signal(signal.SIGTERM, lambda s, f: _signal_handler())

    logger.info("Ctrl+C で停止できます。ダッシュボードから開始/停止を制御してください。")

    # シャットダウンシグナルまで待機
    await shutdown_event.wait()

    # StateMachine が動作中なら停止
    if machine.is_running:
        logger.info("StateMachine を停止中...")
        await machine.stop()
        # ループ終了を少し待つ
        await asyncio.sleep(0.5)

    logger.info("=== DQW AutoBattle System 終了 ===")


if __name__ == "__main__":
    asyncio.run(main())
