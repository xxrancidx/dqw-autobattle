"""ステートマシンのテスト."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.capture.screen import ScreenCapture
from src.control.adb import AdbController
from src.engine.state_machine import GameState, StateMachine
from src.recognition.detector import StateDetector
from src.recognition.matcher import TemplateMatcher


@pytest.fixture()
def state_machine(
    mock_capture: ScreenCapture,
    mock_controller: AdbController,
    templates_dir: object,
) -> StateMachine:
    """テスト用 StateMachine."""
    matcher = MagicMock(spec=TemplateMatcher)
    detector = StateDetector(matcher=matcher)
    return StateMachine(
        capture=mock_capture,
        detector=detector,
        controller=mock_controller,
    )


class TestGameState:
    """GameState Enum のテスト."""

    def test_all_states(self) -> None:
        """SPEC.md の全状態が定義されている."""
        expected = {
            "IDLE", "SEARCHING", "SCROLLING", "TAPPING_ENEMY",
            "IN_BATTLE", "BATTLE_RESULT", "DIALOG_HANDLING", "ERROR",
        }
        actual = {s.name for s in GameState}
        assert actual == expected


class TestStateMachine:
    """StateMachine のテスト."""

    def test_initial_state(self, state_machine: StateMachine) -> None:
        """初期状態が IDLE であること."""
        assert state_machine.state == GameState.IDLE

    def test_not_running_initially(self, state_machine: StateMachine) -> None:
        """初期状態で稼働していないこと."""
        assert not state_machine.is_running

    def test_battle_count_zero(self, state_machine: StateMachine) -> None:
        """初期状態で戦闘回数が 0 であること."""
        assert state_machine.battle_count == 0

    @pytest.mark.asyncio()
    async def test_start_not_implemented(self, state_machine: StateMachine) -> None:
        """start() が NotImplementedError を送出する."""
        with pytest.raises(NotImplementedError):
            await state_machine.start()
