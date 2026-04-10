"""画面キャプチャ層 — ADB screencap によるスクリーンショット取得."""

from __future__ import annotations

import time

import cv2
import numpy as np
from numpy.typing import NDArray

from src.control.adb import AdbController


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
        self._adb = AdbController(device_serial=device_serial)

    def capture(self) -> NDArray[np.uint8]:
        """画面をキャプチャし、numpy 配列（BGR）として返す.

        Returns:
            キャプチャ画像の numpy 配列 (H, W, 3).

        Raises:
            RuntimeError: リトライ回数を超えてもキャプチャに失敗した場合.
        """
        png_bytes = self.capture_png_bytes()
        buf = np.frombuffer(png_bytes, dtype=np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if img is None:
            raise RuntimeError("Failed to decode PNG bytes to image")
        return np.asarray(img, dtype=np.uint8)

    def capture_png_bytes(self) -> bytes:
        """画面をキャプチャし、PNG バイト列として返す.

        Returns:
            PNG 形式のバイト列.

        Raises:
            RuntimeError: リトライ回数を超えてもキャプチャに失敗した場合.
        """
        last_error: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                data = self._adb.screencap()
                if not data:
                    raise RuntimeError("screencap returned empty data")
                return data
            except RuntimeError as e:
                last_error = e
                if attempt < self._max_retries:
                    time.sleep(self._retry_delay)

        raise RuntimeError(
            f"screencap failed after {self._max_retries} retries"
        ) from last_error
