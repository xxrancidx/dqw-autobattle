"""状態認識層 — 画面状態の判定."""

from __future__ import annotations

from enum import Enum, auto

import numpy as np
from numpy.typing import NDArray

from src.recognition.matcher import MatchResult, TemplateMatcher


class ScreenState(Enum):
    """画面の認識状態."""

    FIELD = auto()
    BATTLE = auto()
    BATTLE_RESULT = auto()
    DIALOG = auto()
    WALK_MODE_ON = auto()
    WALK_MODE_OFF = auto()
    ENEMY_SYMBOL = auto()
    UNKNOWN = auto()


class StateDetector:
    """キャプチャ画像から現在の画面状態を判定する.

    Args:
        matcher: テンプレートマッチャーインスタンス.
    """

    def __init__(self, matcher: TemplateMatcher) -> None:
        self._matcher = matcher

    def detect(self, screen: NDArray[np.uint8]) -> ScreenState:
        """画面状態を判定する.

        Args:
            screen: キャプチャ画像の numpy 配列 (H, W, 3).

        Returns:
            判定された画面状態.
        """
        raise NotImplementedError

    def find_enemy(self, screen: NDArray[np.uint8]) -> MatchResult | None:
        """フィールド画面上の敵シンボルを検出する.

        Args:
            screen: キャプチャ画像の numpy 配列 (H, W, 3).

        Returns:
            敵シンボルのマッチ結果. 見つからない場合は None.
        """
        raise NotImplementedError

    def find_dialog_button(self, screen: NDArray[np.uint8]) -> MatchResult | None:
        """ダイアログの OK / 閉じるボタンを検出する.

        Args:
            screen: キャプチャ画像の numpy 配列 (H, W, 3).

        Returns:
            ボタンのマッチ結果. 見つからない場合は None.
        """
        raise NotImplementedError
