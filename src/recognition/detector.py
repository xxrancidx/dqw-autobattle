"""状態認識層 — 画面状態の判定."""

from __future__ import annotations

import logging
from enum import Enum, auto

import numpy as np
from numpy.typing import NDArray

from src.recognition.matcher import MatchResult, TemplateMatcher

logger = logging.getLogger(__name__)


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


# 優先度順の状態定義: (状態, テンプレート名リスト)
_STATE_PRIORITY: list[tuple[ScreenState, list[str]]] = [
    (ScreenState.DIALOG, ["dialog_ok", "dialog_close"]),
    (ScreenState.BATTLE_RESULT, ["battle_result"]),
    (ScreenState.BATTLE, ["battle_attack", "battle_command"]),
    (ScreenState.WALK_MODE_ON, ["walk_mode_on"]),
    (ScreenState.WALK_MODE_OFF, ["walk_mode_off"]),
    (ScreenState.FIELD, ["field_menu", "field_map"]),
]


class StateDetector:
    """キャプチャ画像から現在の画面状態を判定する.

    Args:
        matcher: テンプレートマッチャーインスタンス.
        state_priority: 状態判定の優先度リスト（省略時はデフォルト）.
    """

    def __init__(
        self,
        matcher: TemplateMatcher,
        state_priority: list[tuple[ScreenState, list[str]]] | None = None,
    ) -> None:
        self._matcher = matcher
        self._state_priority = state_priority if state_priority is not None else _STATE_PRIORITY

    def detect(self, screen: NDArray[np.uint8]) -> ScreenState:
        """画面状態を判定する.

        優先度順にテンプレートマッチングを試行し、最初にヒットした状態を返す。

        Args:
            screen: キャプチャ画像の numpy 配列 (H, W, 3).

        Returns:
            判定された画面状態.
        """
        for state, template_names in self._state_priority:
            result = self._matcher.match_any(screen, template_names)
            if result is not None:
                logger.info(
                    "画面状態判定: %s (template=%s, score=%.3f)",
                    state.name,
                    result.template_name,
                    result.score,
                )
                return state

        logger.info("画面状態判定: UNKNOWN")
        return ScreenState.UNKNOWN

    def find_enemy(self, screen: NDArray[np.uint8]) -> MatchResult | None:
        """フィールド画面上の敵シンボルを検出する.

        Args:
            screen: キャプチャ画像の numpy 配列 (H, W, 3).

        Returns:
            敵シンボルのマッチ結果. 見つからない場合は None.
        """
        return self._matcher.match(screen, "enemy_symbol")

    def find_enemies(self, screen: NDArray[np.uint8]) -> list[MatchResult]:
        """フィールド画面上の複数の敵シンボルを検出する.

        Args:
            screen: キャプチャ画像の numpy 配列 (H, W, 3).

        Returns:
            敵シンボルのマッチ結果リスト.
        """
        return self._matcher.match_multi(screen, "enemy_symbol")

    def find_dialog_button(self, screen: NDArray[np.uint8]) -> MatchResult | None:
        """ダイアログの OK / 閉じるボタンを検出する.

        Args:
            screen: キャプチャ画像の numpy 配列 (H, W, 3).

        Returns:
            ボタンのマッチ結果. 見つからない場合は None.
        """
        return self._matcher.match_any(screen, ["dialog_ok", "dialog_close"])
