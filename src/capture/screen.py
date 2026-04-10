"""画面キャプチャ層 — ADB screencap によるスクリーンショット取得."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


class ScreenCapture:
    """ADB screencap コマンドで端末画面を PNG として取得する.

    Args:
        device_serial: ADB デバイスシリアル番号. None の場合はデフォルトデバイスを使用.
        max_retries: screencap 失敗時のリトライ回数.
        retry_delay: リトライ間隔（秒）.
    """

    def __init__(
        self,
        device_serial: str | None = None,
        max_retries: int = 3,
        retry_delay: float = 0.5,
    ) -> None:
        self._device_serial = device_serial
        self._max_retries = max_retries
        self._retry_delay = retry_delay

    def capture(self) -> NDArray[np.uint8]:
        """画面をキャプチャし、numpy 配列（BGR）として返す.

        Returns:
            キャプチャ画像の numpy 配列 (H, W, 3).

        Raises:
            RuntimeError: リトライ回数を超えてもキャプチャに失敗した場合.
        """
        raise NotImplementedError

    def capture_png_bytes(self) -> bytes:
        """画面をキャプチャし、PNG バイト列として返す.

        Returns:
            PNG 形式のバイト列.

        Raises:
            RuntimeError: リトライ回数を超えてもキャプチャに失敗した場合.
        """
        raise NotImplementedError
