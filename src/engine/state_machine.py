"""ステートマシン — メインループの状態遷移管理."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

import numpy as np
from numpy.typing import NDArray

from src.recognition.detector import ScreenState

if TYPE_CHECKING:
    from src.capture.screen import ScreenCapture
    from src.control.adb import AdbController
    from src.recognition.detector import StateDetector

logger = logging.getLogger(__name__)

# Handler signature: (self, screen, screen_state) -> None
_Handler = Callable[["StateMachine", NDArray[np.uint8], ScreenState], None]

# Event callback: async (event_type, data) -> None
EventCallback = Callable[[str, dict[str, Any]], Awaitable[None]]


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
        max_scroll_retry: スクロール探索の最大リトライ回数.
        dialog_retry_count: ダイアログ復帰の最大リトライ回数.
        max_runtime_minutes: 最大実行時間（分）. 0 で無制限.
        tick_interval: ティック間隔（秒）.
        scroll_duration_ms: スクロール操作のスワイプ時間（ミリ秒）.
    """

    def __init__(
        self,
        capture: ScreenCapture,
        detector: StateDetector,
        controller: AdbController,
        *,
        max_scroll_retry: int = 5,
        dialog_retry_count: int = 3,
        max_runtime_minutes: int = 60,
        tick_interval: float = 1.0,
        scroll_duration_ms: int = 2000,
    ) -> None:
        self._capture = capture
        self._detector = detector
        self._controller = controller
        self._max_scroll_retry = max_scroll_retry
        self._dialog_retry_count = dialog_retry_count
        self._max_runtime_minutes = max_runtime_minutes
        self._tick_interval = tick_interval
        self._scroll_duration_ms = scroll_duration_ms

        self._state = GameState.IDLE
        self._running = False
        self._battle_count = 0
        self._error_count = 0
        self._scroll_count = 0
        self._dialog_retries = 0
        self._pre_dialog_state = GameState.SEARCHING
        self._start_time: float = 0.0
        self._event_callbacks: list[EventCallback] = []
        self._last_screen: NDArray[np.uint8] | None = None

    # ------------------------------------------------------------------ #
    #  Properties
    # ------------------------------------------------------------------ #

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

    @property
    def last_screen(self) -> NDArray[np.uint8] | None:
        """最後にキャプチャした画面."""
        return self._last_screen

    # ------------------------------------------------------------------ #
    #  Event system
    # ------------------------------------------------------------------ #

    def add_event_callback(self, callback: EventCallback) -> None:
        """イベントコールバックを登録する."""
        self._event_callbacks.append(callback)

    async def _emit_event(self, event_type: str, data: dict[str, Any]) -> None:
        """登録済みコールバックにイベントを配信する."""
        for cb in self._event_callbacks:
            try:
                await cb(event_type, data)
            except Exception:
                logger.exception("イベントコールバックでエラー")

    # ------------------------------------------------------------------ #
    #  Start / Stop
    # ------------------------------------------------------------------ #

    async def start(self) -> None:
        """ステートマシンを開始する.

        Raises:
            RuntimeError: デバイスが接続されていない場合.
        """
        if not self._controller.device_check():
            raise RuntimeError("デバイスが接続されていません")

        self._running = True
        self._start_time = time.monotonic()
        self._transition(GameState.SEARCHING)
        logger.info("ステートマシン開始")

        try:
            while self._running:
                if self._is_timeout():
                    logger.info("最大実行時間に到達 — 自動停止")
                    break
                await self._tick()
                await asyncio.sleep(self._tick_interval)
        finally:
            self._running = False
            self._transition(GameState.IDLE)
            logger.info(
                "ステートマシン停止: battles=%d, errors=%d",
                self._battle_count,
                self._error_count,
            )

    async def stop(self) -> None:
        """ステートマシンを停止する."""
        logger.info("停止リクエスト受信")
        self._running = False

    # ------------------------------------------------------------------ #
    #  Core loop
    # ------------------------------------------------------------------ #

    async def _tick(self) -> None:
        """1 ティック分の状態遷移を実行する."""
        screen = self._capture.capture()
        self._last_screen = screen
        screen_state = self._detector.detect(screen)

        # どの状態でもダイアログが出たら最優先で処理
        if screen_state == ScreenState.DIALOG and self._state != GameState.DIALOG_HANDLING:
            self._pre_dialog_state = self._state
            self._dialog_retries = 0
            self._transition(GameState.DIALOG_HANDLING)

        handler: _Handler | None = _HANDLERS.get(self._state)
        if handler is not None:
            handler(self, screen, screen_state)

        # 状態更新イベントを配信
        await self._emit_event("status", {
            "state": self._state.name,
            "battle_count": self._battle_count,
            "error_count": self._error_count,
            "running": self._running,
        })

    # ------------------------------------------------------------------ #
    #  State handlers
    # ------------------------------------------------------------------ #

    def _handle_searching(
        self, screen: NDArray[np.uint8], screen_state: ScreenState
    ) -> None:
        """SEARCHING: 敵シンボルを探す."""
        enemy = self._detector.find_enemy(screen)
        if enemy is not None:
            self._scroll_count = 0
            self._transition(GameState.TAPPING_ENEMY)
            self._controller.tap(enemy.x, enemy.y)
            logger.info("敵シンボル発見: pos=(%d,%d)", enemy.x, enemy.y)
        else:
            # 敵が見つからない → スクロールへ
            if self._scroll_count < self._max_scroll_retry:
                self._transition(GameState.SCROLLING)
            else:
                logger.warning("スクロール上限到達 — リセット")
                self._scroll_count = 0
                self._transition(GameState.SEARCHING)

    def _handle_scrolling(
        self, screen: NDArray[np.uint8], screen_state: ScreenState
    ) -> None:
        """SCROLLING: 画面をスクロールして敵を探す."""
        self._scroll_count += 1
        logger.info("スクロール探索: %d/%d", self._scroll_count, self._max_scroll_retry)
        # 画面中央から上方向にスワイプ
        self._controller.swipe(540, 1600, 540, 800, self._scroll_duration_ms)
        self._transition(GameState.SEARCHING)

    def _handle_tapping_enemy(
        self, screen: NDArray[np.uint8], screen_state: ScreenState
    ) -> None:
        """TAPPING_ENEMY: 敵タップ後、戦闘開始を待つ."""
        if screen_state == ScreenState.BATTLE:
            self._transition(GameState.IN_BATTLE)
        elif screen_state == ScreenState.FIELD:
            # タップがミスした — 再探索
            self._transition(GameState.SEARCHING)

    def _handle_in_battle(
        self, screen: NDArray[np.uint8], screen_state: ScreenState
    ) -> None:
        """IN_BATTLE: 戦闘中（オートバトルなので結果を待つ）."""
        if screen_state == ScreenState.BATTLE_RESULT:
            self._transition(GameState.BATTLE_RESULT)

    def _handle_battle_result(
        self, screen: NDArray[np.uint8], screen_state: ScreenState
    ) -> None:
        """BATTLE_RESULT: 戦闘結果画面 → タップして閉じる."""
        self._battle_count += 1
        logger.info("戦闘完了: 累計 %d 回", self._battle_count)
        # 結果画面をタップして閉じる
        self._controller.tap(540, 1200)
        self._transition(GameState.SEARCHING)

    def _handle_dialog(
        self, screen: NDArray[np.uint8], screen_state: ScreenState
    ) -> None:
        """DIALOG_HANDLING: ダイアログを閉じて元の状態に復帰する."""
        btn = self._detector.find_dialog_button(screen)

        if btn is not None:
            self._controller.tap(btn.x, btn.y)
            logger.info("ダイアログボタンタップ: pos=(%d,%d)", btn.x, btn.y)

        self._dialog_retries += 1

        if screen_state != ScreenState.DIALOG:
            # ダイアログが消えた → 復帰
            logger.info("ダイアログ復帰成功")
            self._dialog_retries = 0
            self._transition(self._pre_dialog_state)
        elif self._dialog_retries >= self._dialog_retry_count:
            # リトライ上限 → エラー
            logger.error("ダイアログ復帰失敗: リトライ上限到達")
            self._error_count += 1
            self._transition(GameState.ERROR)

    def _handle_error(
        self, screen: NDArray[np.uint8], screen_state: ScreenState
    ) -> None:
        """ERROR: エラー状態 — 自動停止."""
        logger.error("エラー状態 — 停止")
        self._running = False

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    def _transition(self, new_state: GameState) -> None:
        """状態を遷移させる."""
        old = self._state
        self._state = new_state
        if old != new_state:
            logger.info("状態遷移: %s → %s", old.name, new_state.name)

    def _is_timeout(self) -> bool:
        """最大実行時間を超過したか."""
        if self._max_runtime_minutes <= 0:
            return False
        elapsed = time.monotonic() - self._start_time
        return elapsed >= self._max_runtime_minutes * 60


# Handler dispatch table (module-level to avoid class-body forward references)
_HANDLERS: dict[GameState, _Handler] = {
    GameState.SEARCHING: StateMachine._handle_searching,
    GameState.SCROLLING: StateMachine._handle_scrolling,
    GameState.TAPPING_ENEMY: StateMachine._handle_tapping_enemy,
    GameState.IN_BATTLE: StateMachine._handle_in_battle,
    GameState.BATTLE_RESULT: StateMachine._handle_battle_result,
    GameState.DIALOG_HANDLING: StateMachine._handle_dialog,
    GameState.ERROR: StateMachine._handle_error,
}
