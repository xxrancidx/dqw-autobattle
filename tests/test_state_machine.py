"""ステートマシンのテスト."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.capture.screen import ScreenCapture
from src.control.adb import AdbController
from src.engine.state_machine import GameState, StateMachine
from src.recognition.detector import ScreenState, StateDetector
from src.recognition.matcher import MatchResult

# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #

def _dummy_screen() -> np.ndarray:
    return np.zeros((2400, 1080, 3), dtype=np.uint8)


def _make_sm(
    *,
    detect_returns: list[ScreenState] | None = None,
    find_enemy_returns: list[MatchResult | None] | None = None,
    find_dialog_button_returns: list[MatchResult | None] | None = None,
    max_scroll_retry: int = 5,
    dialog_retry_count: int = 3,
    max_runtime_minutes: int = 0,
    tick_interval: float = 0.0,
) -> StateMachine:
    """全依存をモック化した StateMachine を生成する."""
    capture = MagicMock(spec=ScreenCapture)
    capture.capture.return_value = _dummy_screen()

    detector = MagicMock(spec=StateDetector)
    if detect_returns is not None:
        detector.detect.side_effect = detect_returns
    else:
        detector.detect.return_value = ScreenState.FIELD

    if find_enemy_returns is not None:
        detector.find_enemy.side_effect = find_enemy_returns
    else:
        detector.find_enemy.return_value = None

    if find_dialog_button_returns is not None:
        detector.find_dialog_button.side_effect = find_dialog_button_returns
    else:
        detector.find_dialog_button.return_value = None

    controller = MagicMock(spec=AdbController)
    controller.device_check.return_value = True

    return StateMachine(
        capture=capture,
        detector=detector,
        controller=controller,
        max_scroll_retry=max_scroll_retry,
        dialog_retry_count=dialog_retry_count,
        max_runtime_minutes=max_runtime_minutes,
        tick_interval=tick_interval,
    )


def _enemy_hit(x: int = 500, y: int = 800) -> MatchResult:
    return MatchResult(
        template_name="enemy_symbol", score=0.95, x=x, y=y, width=50, height=50,
    )


def _dialog_btn(x: int = 540, y: int = 1400) -> MatchResult:
    return MatchResult(
        template_name="dialog_ok", score=0.90, x=x, y=y, width=60, height=40,
    )


async def _run_ticks(sm: StateMachine, n: int) -> list[GameState]:
    """n 回 _tick を実行し、各 tick 後の状態を返す."""
    sm._state = GameState.SEARCHING
    states: list[GameState] = []
    for _ in range(n):
        await sm._tick()
        states.append(sm.state)
    return states


# --------------------------------------------------------------------------- #
#  GameState enum
# --------------------------------------------------------------------------- #

class TestGameState:
    def test_all_states(self) -> None:
        expected = {
            "IDLE", "SEARCHING", "SCROLLING", "TAPPING_ENEMY",
            "IN_BATTLE", "BATTLE_RESULT", "DIALOG_HANDLING", "ERROR",
        }
        assert {s.name for s in GameState} == expected


# --------------------------------------------------------------------------- #
#  Basic properties
# --------------------------------------------------------------------------- #

class TestStateMachineBasics:
    def test_initial_state(self) -> None:
        sm = _make_sm()
        assert sm.state == GameState.IDLE
        assert not sm.is_running
        assert sm.battle_count == 0
        assert sm.error_count == 0

    @pytest.mark.asyncio()
    async def test_start_no_device(self) -> None:
        sm = _make_sm()
        sm._controller.device_check.return_value = False  # type: ignore[union-attr]
        with pytest.raises(RuntimeError, match="デバイスが接続されていません"):
            await sm.start()

    @pytest.mark.asyncio()
    async def test_stop(self) -> None:
        sm = _make_sm()
        sm._running = True
        await sm.stop()
        assert not sm._running


# --------------------------------------------------------------------------- #
#  正常フロー: SEARCHING → TAPPING_ENEMY → IN_BATTLE → BATTLE_RESULT → SEARCHING
# --------------------------------------------------------------------------- #

class TestNormalFlow:
    @pytest.mark.asyncio()
    async def test_full_battle_cycle(self) -> None:
        """敵発見 → 戦闘 → 結果 → 再探索 の一巡.

        tick1: SEARCHING, detect=FIELD → find_enemy=hit → TAPPING_ENEMY
        tick2: TAPPING_ENEMY, detect=BATTLE → IN_BATTLE
        tick3: IN_BATTLE, detect=BATTLE_RESULT → BATTLE_RESULT
        tick4: BATTLE_RESULT, detect=FIELD → battle_count++ → SEARCHING
        """
        sm = _make_sm(
            detect_returns=[
                ScreenState.FIELD,          # tick1
                ScreenState.BATTLE,         # tick2
                ScreenState.BATTLE_RESULT,  # tick3
                ScreenState.FIELD,          # tick4
            ],
            find_enemy_returns=[_enemy_hit()],  # tick1 only
        )

        states = await _run_ticks(sm, 4)

        assert states == [
            GameState.TAPPING_ENEMY,  # tick1
            GameState.IN_BATTLE,      # tick2
            GameState.BATTLE_RESULT,  # tick3
            GameState.SEARCHING,      # tick4
        ]
        assert sm.battle_count == 1

    @pytest.mark.asyncio()
    async def test_battle_count_increments(self) -> None:
        """戦闘完了ごとに battle_count がインクリメントされる.

        tick1: SEARCHING → find_enemy → TAPPING_ENEMY
        tick2: TAPPING_ENEMY → IN_BATTLE
        tick3: IN_BATTLE → BATTLE_RESULT
        tick4: BATTLE_RESULT → SEARCHING (count=1)
        tick5: SEARCHING → find_enemy → TAPPING_ENEMY
        tick6: TAPPING_ENEMY → IN_BATTLE
        tick7: IN_BATTLE → BATTLE_RESULT
        tick8: BATTLE_RESULT → SEARCHING (count=2)
        """
        sm = _make_sm(
            detect_returns=[
                ScreenState.FIELD,          # tick1
                ScreenState.BATTLE,         # tick2
                ScreenState.BATTLE_RESULT,  # tick3
                ScreenState.FIELD,          # tick4
                ScreenState.FIELD,          # tick5
                ScreenState.BATTLE,         # tick6
                ScreenState.BATTLE_RESULT,  # tick7
                ScreenState.FIELD,          # tick8
            ],
            find_enemy_returns=[_enemy_hit(), _enemy_hit()],  # tick1, tick5
        )

        await _run_ticks(sm, 8)
        assert sm.battle_count == 2


# --------------------------------------------------------------------------- #
#  スクロール探索: SEARCHING → SCROLLING → SEARCHING → TAPPING_ENEMY
# --------------------------------------------------------------------------- #

class TestScrollSearch:
    @pytest.mark.asyncio()
    async def test_scroll_then_find(self) -> None:
        """敵未発見 → スクロール → 再探索で敵発見.

        tick1: SEARCHING, no enemy → SCROLLING
        tick2: SCROLLING → swipe → SEARCHING
        tick3: SEARCHING, enemy found → TAPPING_ENEMY
        """
        sm = _make_sm(
            max_scroll_retry=3,
            detect_returns=[
                ScreenState.FIELD,  # tick1
                ScreenState.FIELD,  # tick2
                ScreenState.FIELD,  # tick3
            ],
            find_enemy_returns=[None, _enemy_hit()],  # tick1, tick3
        )

        states = await _run_ticks(sm, 3)

        assert states == [
            GameState.SCROLLING,
            GameState.SEARCHING,
            GameState.TAPPING_ENEMY,
        ]
        sm._controller.swipe.assert_called_once()  # type: ignore[union-attr]

    @pytest.mark.asyncio()
    async def test_scroll_retry_limit_resets(self) -> None:
        """スクロール上限到達でリセットされ探索が継続する.

        max_scroll_retry=2:
        tick1: SEARCHING, no enemy, scroll_count(0)<2 → SCROLLING
        tick2: SCROLLING, scroll_count=1 → SEARCHING
        tick3: SEARCHING, no enemy, scroll_count(1)<2 → SCROLLING
        tick4: SCROLLING, scroll_count=2 → SEARCHING
        tick5: SEARCHING, no enemy, scroll_count(2)==2 → reset, SEARCHING
        """
        sm = _make_sm(
            max_scroll_retry=2,
            detect_returns=[ScreenState.FIELD] * 5,
            find_enemy_returns=[None, None, None],  # tick1, tick3, tick5
        )

        states = await _run_ticks(sm, 5)

        assert states[4] == GameState.SEARCHING
        assert sm._scroll_count == 0


# --------------------------------------------------------------------------- #
#  エラーリカバリ: 任意の状態 → DIALOG_HANDLING → 復帰
# --------------------------------------------------------------------------- #

class TestDialogRecovery:
    @pytest.mark.asyncio()
    async def test_dialog_during_battle(self) -> None:
        """戦闘中にダイアログ出現 → 閉じて戦闘復帰.

        tick1: SEARCHING → find_enemy → TAPPING_ENEMY
        tick2: TAPPING_ENEMY, detect=BATTLE → IN_BATTLE
        tick3: IN_BATTLE, detect=DIALOG → DIALOG_HANDLING, handler finds btn, retries=1
        tick4: DIALOG_HANDLING, detect=BATTLE → screen!=DIALOG → restore IN_BATTLE
        """
        sm = _make_sm(
            detect_returns=[
                ScreenState.FIELD,    # tick1
                ScreenState.BATTLE,   # tick2
                ScreenState.DIALOG,   # tick3
                ScreenState.BATTLE,   # tick4
            ],
            find_enemy_returns=[_enemy_hit()],
            find_dialog_button_returns=[_dialog_btn(), None],  # tick3, tick4
        )

        states = await _run_ticks(sm, 4)

        assert states[2] == GameState.DIALOG_HANDLING
        assert states[3] == GameState.IN_BATTLE

    @pytest.mark.asyncio()
    async def test_dialog_during_searching(self) -> None:
        """探索中にダイアログ出現 → 閉じて探索復帰.

        tick1: SEARCHING, detect=DIALOG → DIALOG_HANDLING, finds btn, retries=1
        tick2: DIALOG_HANDLING, detect=FIELD → screen!=DIALOG → restore SEARCHING
        """
        sm = _make_sm(
            detect_returns=[
                ScreenState.DIALOG,  # tick1
                ScreenState.FIELD,   # tick2
            ],
            find_dialog_button_returns=[_dialog_btn(), None],  # tick1, tick2
        )

        states = await _run_ticks(sm, 2)

        assert states[0] == GameState.DIALOG_HANDLING
        assert states[1] == GameState.SEARCHING


# --------------------------------------------------------------------------- #
#  エラー停止: DIALOG_HANDLING でリトライ上限 → ERROR
# --------------------------------------------------------------------------- #

class TestDialogError:
    @pytest.mark.asyncio()
    async def test_dialog_retry_exhausted(self) -> None:
        """ダイアログリトライ上限到達で ERROR.

        dialog_retry_count=2:
        tick1: SEARCHING, detect=DIALOG → DIALOG_HANDLING, retries=1, still DIALOG
        tick2: DIALOG_HANDLING, detect=DIALOG (already in DH, no re-transition),
               retries=2==limit → ERROR
        """
        sm = _make_sm(
            dialog_retry_count=2,
            detect_returns=[
                ScreenState.DIALOG,  # tick1
                ScreenState.DIALOG,  # tick2
            ],
            find_dialog_button_returns=[_dialog_btn(), _dialog_btn()],
        )

        states = await _run_ticks(sm, 2)

        assert states[0] == GameState.DIALOG_HANDLING
        assert states[1] == GameState.ERROR
        assert sm.error_count == 1

    @pytest.mark.asyncio()
    async def test_error_stops_running(self) -> None:
        """ERROR 状態で _running が False になる."""
        sm = _make_sm(detect_returns=[ScreenState.UNKNOWN])
        sm._state = GameState.ERROR

        await sm._tick()
        assert not sm._running


# --------------------------------------------------------------------------- #
#  タイムアウト
# --------------------------------------------------------------------------- #

class TestTimeout:
    @pytest.mark.asyncio()
    async def test_max_runtime_stops(self) -> None:
        """max_runtime_minutes で自動停止する."""
        sm = _make_sm(
            max_runtime_minutes=1,
            detect_returns=[ScreenState.FIELD] * 10,
            find_enemy_returns=[None] * 10,
        )

        with patch("time.monotonic", side_effect=[0.0, 61.0, 61.0]):
            await sm.start()

        assert sm.state == GameState.IDLE
        assert not sm.is_running


# --------------------------------------------------------------------------- #
#  Start → メインループ統合テスト
# --------------------------------------------------------------------------- #

class TestStartIntegration:
    @pytest.mark.asyncio()
    async def test_start_transitions_to_searching(self) -> None:
        """start() で IDLE → SEARCHING に遷移しループが動く."""
        sm = _make_sm(
            detect_returns=[ScreenState.FIELD],
            find_enemy_returns=[None],
        )

        tick_count = 0
        original_tick = sm._tick.__func__  # type: ignore[attr-defined]

        async def counting_tick() -> None:
            nonlocal tick_count
            await original_tick(sm)
            tick_count += 1
            sm._running = False

        sm._tick = counting_tick  # type: ignore[assignment]
        await sm.start()

        assert tick_count == 1
        assert sm.state == GameState.IDLE  # finally で IDLE に戻る
