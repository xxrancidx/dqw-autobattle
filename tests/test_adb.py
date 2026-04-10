"""ADB コントローラのテスト."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from src.control.adb import AdbController


class TestAdbController:
    """AdbController のテスト."""

    def test_init_default(self) -> None:
        """デフォルト引数での初期化."""
        ctrl = AdbController()
        assert ctrl._device_serial is None
        assert ctrl._cooldown == 0.3

    def test_init_custom(self) -> None:
        """カスタム引数での初期化."""
        ctrl = AdbController(device_serial="abc123", cooldown=0.5, timeout=5.0)
        assert ctrl._device_serial == "abc123"
        assert ctrl._cooldown == 0.5
        assert ctrl._timeout == 5.0

    # --- device_check ---

    @patch("src.control.adb.subprocess.run")
    def test_device_check_connected(self, mock_run: MagicMock) -> None:
        """デバイスが接続されている場合 True を返す."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["adb", "devices"],
            returncode=0,
            stdout=b"List of devices attached\nABC123\tdevice\n\n",
            stderr=b"",
        )
        ctrl = AdbController()
        assert ctrl.device_check() is True

    @patch("src.control.adb.subprocess.run")
    def test_device_check_specific_serial(self, mock_run: MagicMock) -> None:
        """指定シリアルのデバイスが接続されている場合 True を返す."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["adb", "-s", "ABC123", "devices"],
            returncode=0,
            stdout=b"List of devices attached\nABC123\tdevice\nDEF456\tdevice\n\n",
            stderr=b"",
        )
        ctrl = AdbController(device_serial="ABC123")
        assert ctrl.device_check() is True

    @patch("src.control.adb.subprocess.run")
    def test_device_check_serial_not_found(self, mock_run: MagicMock) -> None:
        """指定シリアルのデバイスが見つからない場合 False を返す."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["adb", "-s", "ABC123", "devices"],
            returncode=0,
            stdout=b"List of devices attached\nDEF456\tdevice\n\n",
            stderr=b"",
        )
        ctrl = AdbController(device_serial="ABC123")
        assert ctrl.device_check() is False

    @patch("src.control.adb.subprocess.run")
    def test_device_check_no_devices(self, mock_run: MagicMock) -> None:
        """デバイスが接続されていない場合 False を返す."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["adb", "devices"],
            returncode=0,
            stdout=b"List of devices attached\n\n",
            stderr=b"",
        )
        ctrl = AdbController()
        assert ctrl.device_check() is False

    @patch("src.control.adb.subprocess.run")
    def test_device_check_unauthorized(self, mock_run: MagicMock) -> None:
        """unauthorized デバイスは接続扱いにならない."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["adb", "devices"],
            returncode=0,
            stdout=b"List of devices attached\nABC123\tunauthorized\n\n",
            stderr=b"",
        )
        ctrl = AdbController()
        assert ctrl.device_check() is False

    @patch("src.control.adb.subprocess.run")
    def test_device_check_timeout(self, mock_run: MagicMock) -> None:
        """タイムアウト時は False を返す."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="adb devices", timeout=10)
        ctrl = AdbController()
        assert ctrl.device_check() is False

    # --- tap ---

    @patch("src.control.adb.time.sleep")
    @patch("src.control.adb.time.monotonic")
    @patch("src.control.adb.subprocess.run")
    def test_tap_sends_correct_command(
        self, mock_run: MagicMock, mock_monotonic: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """tap() が正しい ADB コマンドを送信する."""
        mock_monotonic.return_value = 100.0
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=b"", stderr=b"",
        )
        ctrl = AdbController(cooldown=0.3)
        ctrl.tap(540, 1200)

        mock_run.assert_called_once_with(
            ["adb", "shell", "input", "tap", "540", "1200"],
            capture_output=True,
            timeout=10.0,
        )

    @patch("src.control.adb.time.sleep")
    @patch("src.control.adb.time.monotonic")
    @patch("src.control.adb.subprocess.run")
    def test_tap_with_serial(
        self, mock_run: MagicMock, mock_monotonic: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """シリアル指定時に -s オプションが付く."""
        mock_monotonic.return_value = 100.0
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=b"", stderr=b"",
        )
        ctrl = AdbController(device_serial="XYZ789", cooldown=0.3)
        ctrl.tap(100, 200)

        mock_run.assert_called_once_with(
            ["adb", "-s", "XYZ789", "shell", "input", "tap", "100", "200"],
            capture_output=True,
            timeout=10.0,
        )

    @patch("src.control.adb.time.sleep")
    @patch("src.control.adb.time.monotonic")
    @patch("src.control.adb.subprocess.run")
    def test_tap_failure_raises_runtime_error(
        self, mock_run: MagicMock, mock_monotonic: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """tap() 失敗時に RuntimeError を送出する."""
        mock_monotonic.return_value = 100.0
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout=b"", stderr=b"error",
        )
        ctrl = AdbController()
        with pytest.raises(RuntimeError, match="ADB command failed"):
            ctrl.tap(540, 1200)

    @patch("src.control.adb.time.sleep")
    @patch("src.control.adb.time.monotonic")
    @patch("src.control.adb.subprocess.run")
    def test_tap_timeout_raises_runtime_error(
        self, mock_run: MagicMock, mock_monotonic: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """tap() タイムアウト時に RuntimeError を送出する."""
        mock_monotonic.return_value = 100.0
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="adb", timeout=10)
        ctrl = AdbController()
        with pytest.raises(RuntimeError, match="timed out"):
            ctrl.tap(540, 1200)

    # --- swipe ---

    @patch("src.control.adb.time.sleep")
    @patch("src.control.adb.time.monotonic")
    @patch("src.control.adb.subprocess.run")
    def test_swipe_sends_correct_command(
        self, mock_run: MagicMock, mock_monotonic: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """swipe() が正しい ADB コマンドを送信する."""
        mock_monotonic.return_value = 100.0
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=b"", stderr=b"",
        )
        ctrl = AdbController(cooldown=0.3)
        ctrl.swipe(540, 1500, 540, 900, duration_ms=2000)

        mock_run.assert_called_once_with(
            ["adb", "shell", "input", "swipe", "540", "1500", "540", "900", "2000"],
            capture_output=True,
            timeout=10.0,
        )

    @patch("src.control.adb.time.sleep")
    @patch("src.control.adb.time.monotonic")
    @patch("src.control.adb.subprocess.run")
    def test_swipe_default_duration(
        self, mock_run: MagicMock, mock_monotonic: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """swipe() デフォルト duration_ms=500 が渡される."""
        mock_monotonic.return_value = 100.0
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=b"", stderr=b"",
        )
        ctrl = AdbController()
        ctrl.swipe(0, 0, 100, 100)

        mock_run.assert_called_once_with(
            ["adb", "shell", "input", "swipe", "0", "0", "100", "100", "500"],
            capture_output=True,
            timeout=10.0,
        )

    @patch("src.control.adb.time.sleep")
    @patch("src.control.adb.time.monotonic")
    @patch("src.control.adb.subprocess.run")
    def test_swipe_failure_raises_runtime_error(
        self, mock_run: MagicMock, mock_monotonic: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """swipe() 失敗時に RuntimeError を送出する."""
        mock_monotonic.return_value = 100.0
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout=b"", stderr=b"error",
        )
        ctrl = AdbController()
        with pytest.raises(RuntimeError, match="ADB command failed"):
            ctrl.swipe(540, 1500, 540, 900)

    # --- screencap ---

    @patch("src.control.adb.subprocess.run")
    def test_screencap_returns_bytes(self, mock_run: MagicMock) -> None:
        """screencap() が PNG バイト列を返す."""
        png_data = b"\x89PNG\r\n\x1a\nfakedata"
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=png_data, stderr=b"",
        )
        ctrl = AdbController()
        result = ctrl.screencap()
        assert result == png_data

    @patch("src.control.adb.subprocess.run")
    def test_screencap_failure(self, mock_run: MagicMock) -> None:
        """screencap() 失敗時に RuntimeError を送出する."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout=b"", stderr=b"error",
        )
        ctrl = AdbController()
        with pytest.raises(RuntimeError):
            ctrl.screencap()

    # --- cooldown ---

    @patch("src.control.adb.time.sleep")
    @patch("src.control.adb.time.monotonic")
    @patch("src.control.adb.subprocess.run")
    def test_cooldown_waits_between_taps(
        self, mock_run: MagicMock, mock_monotonic: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """連続タップ時にクールダウンの sleep が呼ばれる."""
        # _wait_cooldown は monotonic を2回呼ぶ（elapsed計算 + 記録）
        # 1回目 tap: elapsed=100-0=100 → cooldown不要, 記録=100.0
        # 2回目 tap: elapsed=100.1-100.0=0.1 → sleep(0.2), 記録=100.1
        mock_monotonic.side_effect = [100.0, 100.0, 100.1, 100.1]
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=b"", stderr=b"",
        )
        ctrl = AdbController(cooldown=0.3)
        ctrl.tap(100, 100)
        ctrl.tap(200, 200)

        # 2回目のタップでクールダウン sleep が呼ばれる
        assert mock_sleep.call_count == 1
        sleep_duration = mock_sleep.call_args[0][0]
        assert 0.15 < sleep_duration < 0.25

    @pytest.mark.integration()
    def test_tap_with_device(self) -> None:
        """実デバイスでのタップテスト（ADB 接続必須）."""
        pytest.skip("ADB デバイス未接続")
