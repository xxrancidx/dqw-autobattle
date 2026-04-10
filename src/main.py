"""エントリポイント — 各コンポーネントの初期化と起動."""

from __future__ import annotations

import asyncio
from pathlib import Path

import yaml

from src.capture.screen import ScreenCapture
from src.control.adb import AdbController
from src.engine.state_machine import StateMachine
from src.logging.logger import setup_logging
from src.recognition.detector import StateDetector
from src.recognition.matcher import TemplateMatcher


def load_config(config_path: Path) -> dict[str, object]:
    """設定ファイルを読み込む.

    Args:
        config_path: config.yaml のパス.

    Returns:
        設定値の辞書.
    """
    with open(config_path) as f:
        config: dict[str, object] = yaml.safe_load(f)
    return config


async def main() -> None:
    """アプリケーションのメインエントリポイント."""
    config_path = Path("config.yaml")
    config = load_config(config_path)

    # ロガー設定
    log_dir = Path(str(config.get("log_dir", "logs")))
    setup_logging(log_dir=log_dir)

    # 各コンポーネントの初期化
    capture_conf = config.get("capture", {})
    assert isinstance(capture_conf, dict)

    raw_serial = capture_conf.get("device_serial")
    capture = ScreenCapture(
        device_serial=str(raw_serial) if raw_serial else None,
        max_retries=int(capture_conf.get("max_retries", 3)),
        retry_delay=float(capture_conf.get("retry_delay", 0.5)),
    )

    templates_dir = Path(str(config.get("templates_dir", "templates")))
    recognition_conf = config.get("recognition", {})
    assert isinstance(recognition_conf, dict)

    matcher = TemplateMatcher(
        templates_dir=templates_dir,
        threshold=float(recognition_conf.get("threshold", 0.8)),
    )
    matcher.load_templates()

    detector = StateDetector(matcher=matcher)

    control_conf = config.get("control", {})
    assert isinstance(control_conf, dict)

    ctrl_serial = control_conf.get("device_serial")
    controller = AdbController(
        device_serial=str(ctrl_serial) if ctrl_serial else None,
        cooldown=float(control_conf.get("cooldown", 0.3)),
    )

    state_machine_conf = config.get("state_machine", {})
    assert isinstance(state_machine_conf, dict)

    machine = StateMachine(
        capture=capture,
        detector=detector,
        controller=controller,
        max_dialog_retries=int(state_machine_conf.get("max_dialog_retries", 3)),
    )

    await machine.start()


if __name__ == "__main__":
    asyncio.run(main())
