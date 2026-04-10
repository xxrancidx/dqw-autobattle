"""画面キャプチャ層のテスト."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from src.capture.screen import ScreenCapture


def _make_png_bytes(width: int = 4, height: int = 4) -> bytes:
    """テスト用の有効な PNG バイト列を生成する."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[0, 0] = [255, 0, 0]  # 左上に青ピクセル
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()


class TestScreenCapture:
    """ScreenCapture のテスト."""

    def test_init_default(self) -> None:
        """デフォルト引数での初期化."""
        sc = ScreenCapture()
        assert sc._device_serial is None
        assert sc._max_retries == 3

    def test_init_custom(self) -> None:
        """カスタム引数での初期化."""
        sc = ScreenCapture(device_serial="ABC123", max_retries=5, retry_delay=1.0)
        assert sc._device_serial == "ABC123"
        assert sc._max_retries == 5
        assert sc._retry_delay == 1.0

    # --- capture_png_bytes 正常系 ---

    @patch("src.capture.screen.time.sleep")
    def test_capture_png_bytes_success(self, mock_sleep: MagicMock) -> None:
        """正常にPNGバイト列を取得できる."""
        png_data = _make_png_bytes()
        sc = ScreenCapture()
        with patch.object(sc._adb, "screencap", return_value=png_data):
            result = sc.capture_png_bytes()
        assert result == png_data

    # --- capture_png_bytes 異常系: 空バイナリ ---

    @patch("src.capture.screen.time.sleep")
    def test_capture_png_bytes_empty_data_retries(self, mock_sleep: MagicMock) -> None:
        """空データを返した場合リトライし、最終的に RuntimeError を送出する."""
        sc = ScreenCapture(max_retries=3, retry_delay=0.1)
        with (
            patch.object(sc._adb, "screencap", return_value=b""),
            pytest.raises(RuntimeError, match="failed after 3 retries"),
        ):
            sc.capture_png_bytes()
        # リトライ間に sleep が呼ばれる（最後の試行後は呼ばれない）
        assert mock_sleep.call_count == 2

    # --- capture_png_bytes 異常系: タイムアウト ---

    @patch("src.capture.screen.time.sleep")
    def test_capture_png_bytes_timeout_retries(self, mock_sleep: MagicMock) -> None:
        """screencap がタイムアウトした場合リトライする."""
        sc = ScreenCapture(max_retries=2, retry_delay=0.1)
        with patch.object(
            sc._adb, "screencap", side_effect=RuntimeError("timed out")
        ), pytest.raises(RuntimeError, match="failed after 2 retries"):
            sc.capture_png_bytes()
        assert mock_sleep.call_count == 1

    # --- capture_png_bytes: リトライ後に成功 ---

    @patch("src.capture.screen.time.sleep")
    def test_capture_png_bytes_succeeds_after_retry(self, mock_sleep: MagicMock) -> None:
        """1回目失敗、2回目で成功する."""
        png_data = _make_png_bytes()
        sc = ScreenCapture(max_retries=3, retry_delay=0.1)
        with patch.object(
            sc._adb, "screencap", side_effect=[RuntimeError("fail"), png_data]
        ):
            result = sc.capture_png_bytes()
        assert result == png_data
        assert mock_sleep.call_count == 1

    # --- capture 正常系 ---

    @patch("src.capture.screen.time.sleep")
    def test_capture_returns_ndarray(self, mock_sleep: MagicMock) -> None:
        """capture() が numpy ndarray（BGR）を返す."""
        png_data = _make_png_bytes(width=8, height=6)
        sc = ScreenCapture()
        with patch.object(sc._adb, "screencap", return_value=png_data):
            img = sc.capture()
        assert isinstance(img, np.ndarray)
        assert img.shape == (6, 8, 3)
        assert img.dtype == np.uint8

    # --- capture 異常系: デコード失敗 ---

    @patch("src.capture.screen.time.sleep")
    def test_capture_decode_failure(self, mock_sleep: MagicMock) -> None:
        """不正な PNG データでデコードに失敗した場合 RuntimeError を送出する."""
        sc = ScreenCapture()
        with (
            patch.object(sc._adb, "screencap", return_value=b"not-a-png"),
            pytest.raises(RuntimeError, match="Failed to decode"),
        ):
            sc.capture()

    @pytest.mark.integration()
    def test_capture_with_device(self) -> None:
        """実デバイスでのキャプチャテスト（ADB 接続必須）."""
        pytest.skip("ADB デバイス未接続")
