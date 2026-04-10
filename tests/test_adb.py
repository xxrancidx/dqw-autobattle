"""ADB コントローラのテスト."""

from __future__ import annotations

import pytest

from src.control.adb import AdbController


class TestAdbController:
    """AdbController のテスト."""

    def test_init_default(self) -> None:
        """デフォルト引数での初期化."""
        ctrl = AdbController()
        assert ctrl._device_serial is None
        assert ctrl._cooldown == 0.3

    def test_device_check_not_implemented(self) -> None:
        """device_check() が NotImplementedError を送出する."""
        ctrl = AdbController()
        with pytest.raises(NotImplementedError):
            ctrl.device_check()

    def test_tap_not_implemented(self) -> None:
        """tap() が NotImplementedError を送出する."""
        ctrl = AdbController()
        with pytest.raises(NotImplementedError):
            ctrl.tap(540, 1200)

    def test_swipe_not_implemented(self) -> None:
        """swipe() が NotImplementedError を送出する."""
        ctrl = AdbController()
        with pytest.raises(NotImplementedError):
            ctrl.swipe(540, 1500, 540, 900)

    @pytest.mark.integration()
    def test_tap_with_device(self) -> None:
        """実デバイスでのタップテスト（ADB 接続必須）."""
        pytest.skip("ADB デバイス未接続")
