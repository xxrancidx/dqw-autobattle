"""状態認識層 — OpenCV テンプレートマッチング."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class MatchResult:
    """テンプレートマッチングの結果.

    Attributes:
        template_name: マッチしたテンプレート名.
        score: マッチングスコア（0.0〜1.0）.
        x: 検出位置の中心 X 座標.
        y: 検出位置の中心 Y 座標.
        width: テンプレートの幅.
        height: テンプレートの高さ.
    """

    template_name: str
    score: float
    x: int
    y: int
    width: int
    height: int


class TemplateMatcher:
    """OpenCV テンプレートマッチングによる画像認識.

    Args:
        templates_dir: テンプレート画像ディレクトリのパス.
        threshold: マッチング閾値（デフォルト 0.8）.
    """

    def __init__(
        self,
        templates_dir: Path,
        threshold: float = 0.8,
    ) -> None:
        self._templates_dir = templates_dir
        self._threshold = threshold

    def load_templates(self) -> None:
        """テンプレート画像をディレクトリから読み込む.

        Raises:
            FileNotFoundError: テンプレートディレクトリが存在しない場合.
        """
        raise NotImplementedError

    def match(
        self,
        screen: NDArray[np.uint8],
        template_name: str,
    ) -> MatchResult | None:
        """指定テンプレートで画面をマッチングする.

        Args:
            screen: キャプチャ画像の numpy 配列 (H, W, 3).
            template_name: マッチング対象のテンプレート名.

        Returns:
            閾値以上のマッチ結果. 見つからない場合は None.
        """
        raise NotImplementedError

    def match_any(
        self,
        screen: NDArray[np.uint8],
        template_names: list[str],
    ) -> MatchResult | None:
        """複数テンプレートのうち最もスコアの高いマッチ結果を返す.

        Args:
            screen: キャプチャ画像の numpy 配列 (H, W, 3).
            template_names: マッチング対象のテンプレート名リスト.

        Returns:
            最高スコアのマッチ結果. すべて閾値未満の場合は None.
        """
        raise NotImplementedError
