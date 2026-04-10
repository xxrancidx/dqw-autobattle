"""ステートマシン — メインループの状態遷移管理."""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.capture.screen import ScreenCapture
    from src.control.adb import AdbController
    from src.recognition.detector import StateDetector


class GameState(Enum):
    """ステートマシンの状態.

    SPEC.md セクション 3.2.4 の状態遷移表に対応する.
    """

    IDLE = auto()
    SEARCHING = auto()
    SCROLLING = auto()
    TAPPING_ENEMY = auto()
    IN_BATTLE = auto()
    BATTLE_RESULT = auto()
    DIALOG_HANDLING = auto()
    ERROR = auto()


class StateMachine:
    """有限オートマトンによるゲーム状態遷移を管理する.

    Args:
        capture: 画面キャプチャインスタンス.
        detector: 画面状態検出インスタンス.
        controller: ADB 操作コントローラ.
        max_dialog_retries: ダイアログ復帰の最大リトライ回数.
    """

    def __init__(
        self,
        capture: ScreenCapture,
        detector: StateDetector,
        controller: AdbController,
        max_dialog_retries: int = 3,
    ) -> None:
        self._capture = capture
        self._detector = detector
        self._controller = controller
        self._max_dialog_retries = max_dialog_retries
        self._state = GameState.IDLE
        self._running = False
        self._battle_count = 0
        self._error_count = 0

    @property
    def state(self) -> GameState:
        """現在のステートマシン状態."""
        return self._state

    @property
    def is_running(self) -> bool:
        """ステートマシンが稼働中かどうか."""
        return self._running

    @property
    def battle_count(self) -> int:
        """戦闘回数."""
        return self._battle_count

    @property
    def error_count(self) -> int:
        """エラー発生回数."""
        return self._error_count

    async def start(self) -> None:
        """ステートマシンを開始する.

        Raises:
            RuntimeError: デバイスが接続されていない場合.
        """
        raise NotImplementedError

    async def stop(self) -> None:
        """ステートマシンを停止する."""
        raise NotImplementedError

    async def _tick(self) -> None:
        """1 ティック分の状態遷移を実行する."""
        raise NotImplementedError

    def _transition(self, new_state: GameState) -> None:
        """状態を遷移させる.

        Args:
            new_state: 遷移先の状態.
        """
        raise NotImplementedError
