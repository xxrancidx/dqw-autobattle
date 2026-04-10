"""操作実行層 — ADB コマンド送信."""

from __future__ import annotations


class AdbController:
    """ADB 経由で端末を操作する.

    Args:
        device_serial: ADB デバイスシリアル番号. None の場合はデフォルトデバイスを使用.
        cooldown: 操作間の最低クールダウン（秒）.
    """

    def __init__(
        self,
        device_serial: str | None = None,
        cooldown: float = 0.3,
    ) -> None:
        self._device_serial = device_serial
        self._cooldown = cooldown

    def device_check(self) -> bool:
        """ADB デバイスの接続状態を確認する.

        Returns:
            デバイスが接続されている場合 True.
        """
        raise NotImplementedError

    def tap(self, x: int, y: int) -> None:
        """指定座標をタップする.

        Args:
            x: タップ先の X 座標.
            y: タップ先の Y 座標.

        Raises:
            RuntimeError: ADB コマンドの実行に失敗した場合.
        """
        raise NotImplementedError

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
        raise NotImplementedError

    def screencap(self) -> bytes:
        """スクリーンショットを PNG バイト列として取得する.

        Returns:
            PNG 形式のバイト列.

        Raises:
            RuntimeError: ADB コマンドの実行に失敗した場合.
        """
        raise NotImplementedError
