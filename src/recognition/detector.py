"""状態認識層 — 画面状態の判定."""

from __future__ import annotations

import logging
from enum import Enum, auto

import cv2
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
        """フィールド画面上の敵シンボル（!吹き出し）を検出する.

        全 enemy_symbol* テンプレートをマルチスケールで試行し、
        マッチ位置にオレンジ色が含まれるか検証して誤検出を抑制する。

        Args:
            screen: キャプチャ画像の numpy 配列 (H, W, 3).

        Returns:
            敵シンボルのマッチ結果. 見つからない場合は None.
        """
        enemy_templates = [
            name for name in self._matcher.template_names
            if name.startswith("enemy_symbol")
        ]
        if not enemy_templates:
            logger.warning("enemy_symbol* テンプレートが見つかりません")
            return None

        # 全テンプレートの結果を収集し、オレンジ検証を通過したもののみ採用
        candidates: list[MatchResult] = []
        for name in enemy_templates:
            result = self._matcher.match_multiscale(screen, name)
            if result is not None:
                if self._verify_orange(screen, result):
                    candidates.append(result)
                else:
                    logger.debug(
                        "オレンジ色検証失敗: %s score=%.3f pos=(%d,%d)",
                        name,
                        result.score,
                        result.x,
                        result.y,
                    )

        if not candidates:
            return None

        best = max(candidates, key=lambda r: r.score)
        return best

    def find_enemies(self, screen: NDArray[np.uint8]) -> list[MatchResult]:
        """フィールド画面上の複数の敵シンボルを検出する.

        Args:
            screen: キャプチャ画像の numpy 配列 (H, W, 3).

        Returns:
            敵シンボルのマッチ結果リスト.
        """
        return self._matcher.match_multi(screen, "enemy_symbol")

    @staticmethod
    def _verify_orange(
        screen: NDArray[np.uint8],
        match: MatchResult,
        min_ratio: float = 0.08,
    ) -> bool:
        """マッチ位置の周辺にオレンジ色が一定割合以上存在するか検証する."""
        h, w = screen.shape[:2]
        x0 = max(0, match.x - match.width // 2)
        y0 = max(0, match.y - match.height // 2)
        x1 = min(w, match.x + match.width // 2)
        y1 = min(h, match.y + match.height // 2)

        roi = screen[y0:y1, x0:x1]
        if roi.size == 0:
            return False

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        # オレンジ色範囲: H=5-25, S>80, V>120
        lower = np.array([5, 80, 120], dtype=np.uint8)
        upper = np.array([25, 255, 255], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower, upper)
        ratio = float(np.count_nonzero(mask)) / (roi.shape[0] * roi.shape[1])
        logger.debug("オレンジ色検証: pos=(%d,%d) ratio=%.2f%%", match.x, match.y, ratio * 100)
        return bool(ratio >= min_ratio)

    def find_dialog_button(self, screen: NDArray[np.uint8]) -> MatchResult | None:
        """ダイアログの OK / 閉じるボタンを検出する.

        Args:
            screen: キャプチャ画像の numpy 配列 (H, W, 3).

        Returns:
            ボタンのマッチ結果. 見つからない場合は None.
        """
        return self._matcher.match_any(screen, ["dialog_ok", "dialog_close"])
