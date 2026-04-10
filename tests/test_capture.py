"""画面キャプチャ層のテスト."""

from __future__ import annotations

import pytest

from src.capture.screen import ScreenCapture


class TestScreenCapture:
    """ScreenCapture のテスト."""

    def test_init_default(self) -> None:
        """デフォルト引数での初期化."""
        sc = ScreenCapture()
        assert sc._device_serial is None
        assert sc._max_retries == 3

    def test_capture_not_implemented(self) -> None:
        """capture() が NotImplementedError を送出する."""
        sc = ScreenCapture()
        with pytest.raises(NotImplementedError):
            sc.capture()

    def test_capture_png_bytes_not_implemented(self) -> None:
        """capture_png_bytes() が NotImplementedError を送出する."""
        sc = ScreenCapture()
        with pytest.raises(NotImplementedError):
            sc.capture_png_bytes()

    @pytest.mark.integration()
    def test_capture_with_device(self) -> None:
        """実デバイスでのキャプチャテスト（ADB 接続必須）."""
        pytest.skip("ADB デバイス未接続")
