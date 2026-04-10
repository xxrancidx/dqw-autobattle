"""画面状態判定のテスト."""

from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray

from src.recognition.detector import ScreenState, StateDetector
from src.recognition.matcher import TemplateMatcher


class TestScreenState:
    """ScreenState Enum のテスト."""

    def test_states_exist(self) -> None:
        """すべての状態が定義されている."""
        assert ScreenState.FIELD is not None
        assert ScreenState.BATTLE is not None
        assert ScreenState.DIALOG is not None
        assert ScreenState.UNKNOWN is not None


class TestStateDetector:
    """StateDetector のテスト."""

    def test_detect_not_implemented(
        self, matcher: TemplateMatcher, sample_screen: NDArray[np.uint8]
    ) -> None:
        """detect() が NotImplementedError を送出する."""
        detector = StateDetector(matcher=matcher)
        with pytest.raises(NotImplementedError):
            detector.detect(sample_screen)

    def test_find_enemy_not_implemented(
        self, matcher: TemplateMatcher, sample_screen: NDArray[np.uint8]
    ) -> None:
        """find_enemy() が NotImplementedError を送出する."""
        detector = StateDetector(matcher=matcher)
        with pytest.raises(NotImplementedError):
            detector.find_enemy(sample_screen)
