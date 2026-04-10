"""操作実行層 — ADB コマンド送信."""

from __future__ import annotations

import subprocess
import time


class AdbController:
    """ADB 経由で端末を操作する.

    Args:
        device_serial: ADB デバイスシリアル番号. None の場合はデフォルトデバイスを使用.
        cooldown: 操作間の最低クールダウン（秒）.
        timeout: ADB コマンドのタイムアウト（秒）.
    """

    def __init__(
        self,
        device_serial: str | None = None,
        cooldown: float = 0.3,
        timeout: float = 10.0,
    ) -> None:
        self._device_serial = device_serial
        self._cooldown = cooldown
        self._timeout = timeout
        self._last_action_time: float = 0.0

    def _base_cmd(self) -> list[str]:
        """ADB コマンドのベース部分を組み立てる."""
        cmd = ["adb"]
        if self._device_serial:
            cmd.extend(["-s", self._device_serial])
        return cmd

    def _run(
        self, args: list[str], *, capture_output: bool = True
    ) -> subprocess.CompletedProcess[bytes]:
        """ADB コマンドを実行する.

        Raises:
            RuntimeError: コマンドの実行に失敗した場合.
        """
        cmd = self._base_cmd() + args
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                timeout=self._timeout,
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"ADB command timed out: {' '.join(cmd)}") from e

        if result.returncode != 0:
            raise RuntimeError(
                f"ADB command failed (rc={result.returncode}): {' '.join(cmd)}"
            )
        return result

    def _wait_cooldown(self) -> None:
        """前回の操作からクールダウン時間が経過するまで待機する."""
        elapsed = time.monotonic() - self._last_action_time
        remaining = self._cooldown - elapsed
        if remaining > 0:
            time.sleep(remaining)
        self._last_action_time = time.monotonic()

    def device_check(self) -> bool:
        """ADB デバイスの接続状態を確認する.

        Returns:
            デバイスが接続されている場合 True.
        """
        cmd = self._base_cmd() + ["devices"]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=self._timeout,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

        if result.returncode != 0:
            return False

        output = result.stdout.decode("utf-8", errors="replace")
        lines = output.strip().splitlines()
        # 先頭行は "List of devices attached"、以降がデバイス行
        for line in lines[1:]:
            parts = line.strip().split("\t")
            if (
                len(parts) >= 2
                and parts[1] == "device"
                and (self._device_serial is None or parts[0] == self._device_serial)
            ):
                return True
        return False

    def tap(self, x: int, y: int) -> None:
        """指定座標をタップする.

        Args:
            x: タップ先の X 座標.
            y: タップ先の Y 座標.

        Raises:
            RuntimeError: ADB コマンドの実行に失敗した場合.
        """
        self._wait_cooldown()
        self._run(["shell", "input", "tap", str(x), str(y)])

    def swipe(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration_ms: int = 500,
    ) -> None:
        """スワイプ操作を実行する.

        Args:
            x1: スワイプ開始 X 座標.
            y1: スワイプ開始 Y 座標.
            x2: スワイプ終了 X 座標.
            y2: スワイプ終了 Y 座標.
            duration_ms: スワイプにかける時間（ミリ秒）.

        Raises:
            RuntimeError: ADB コマンドの実行に失敗した場合.
        """
        self._wait_cooldown()
        self._run([
            "shell", "input", "swipe",
            str(x1), str(y1), str(x2), str(y2), str(duration_ms),
        ])

    def screencap(self) -> bytes:
        """スクリーンショットを PNG バイト列として取得する.

        Returns:
            PNG 形式のバイト列.

        Raises:
            RuntimeError: ADB コマンドの実行に失敗した場合.
        """
        result = self._run(["exec-out", "screencap", "-p"])
        return result.stdout
