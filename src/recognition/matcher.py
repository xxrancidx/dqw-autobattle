"""状態認識層 — OpenCV テンプレートマッチング."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)


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
        self._templates: dict[str, NDArray[np.uint8]] = {}

    @property
    def template_names(self) -> list[str]:
        """読み込み済みテンプレート名のリストを返す."""
        return list(self._templates.keys())

    def load_templates(self) -> None:
        """テンプレート画像をディレクトリから読み込む.

        Raises:
            FileNotFoundError: テンプレートディレクトリが存在しない場合.
        """
        if not self._templates_dir.exists():
            raise FileNotFoundError(
                f"テンプレートディレクトリが見つかりません: {self._templates_dir}"
            )

        self._templates.clear()
        for path in sorted(self._templates_dir.glob("*.png")):
            raw = np.fromfile(str(path), dtype=np.uint8)
            img = cv2.imdecode(raw, cv2.IMREAD_COLOR)
            if img is None:
                logger.warning("テンプレート読み込み失敗: %s", path.name)
                continue
            name = path.stem
            self._templates[name] = np.asarray(img, dtype=np.uint8)
            logger.debug("テンプレート読み込み: %s (%dx%d)", name, img.shape[1], img.shape[0])

        logger.info("テンプレート %d 件を読み込みました", len(self._templates))

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
        tmpl = self._templates.get(template_name)
        if tmpl is None:
            logger.warning("テンプレート未登録: %s", template_name)
            return None

        th, tw = tmpl.shape[:2]
        if screen.shape[0] < th or screen.shape[1] < tw:
            logger.warning(
                "画面がテンプレートより小さい: screen=%s, template=%s",
                screen.shape[:2],
                tmpl.shape[:2],
            )
            return None

        result = cv2.matchTemplate(screen, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val < self._threshold:
            logger.debug(
                "マッチング閾値未満: %s score=%.3f < %.3f",
                template_name,
                max_val,
                self._threshold,
            )
            return None

        cx = max_loc[0] + tw // 2
        cy = max_loc[1] + th // 2
        match_result = MatchResult(
            template_name=template_name,
            score=float(max_val),
            x=cx,
            y=cy,
            width=tw,
            height=th,
        )
        logger.info(
            "マッチング成功: %s score=%.3f pos=(%d,%d)",
            template_name,
            max_val,
            cx,
            cy,
        )
        return match_result

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
        best: MatchResult | None = None
        for name in template_names:
            result = self.match(screen, name)
            if result is not None and (best is None or result.score > best.score):
                best = result
        return best

    def match_multi(
        self,
        screen: NDArray[np.uint8],
        template_name: str,
        *,
        max_count: int = 10,
    ) -> list[MatchResult]:
        """同一テンプレートの複数マッチを検出する（敵シンボル等）.

        Args:
            screen: キャプチャ画像の numpy 配列 (H, W, 3).
            template_name: マッチング対象のテンプレート名.
            max_count: 最大検出数.

        Returns:
            閾値以上のマッチ結果リスト（スコア降順）.
        """
        tmpl = self._templates.get(template_name)
        if tmpl is None:
            logger.warning("テンプレート未登録: %s", template_name)
            return []

        th, tw = tmpl.shape[:2]
        if screen.shape[0] < th or screen.shape[1] < tw:
            return []

        result_map = cv2.matchTemplate(screen, tmpl, cv2.TM_CCOEFF_NORMED)
        results: list[MatchResult] = []

        for _ in range(max_count):
            _, max_val, _, max_loc = cv2.minMaxLoc(result_map)
            if max_val < self._threshold:
                break

            cx = max_loc[0] + tw // 2
            cy = max_loc[1] + th // 2
            results.append(
                MatchResult(
                    template_name=template_name,
                    score=float(max_val),
                    x=cx,
                    y=cy,
                    width=tw,
                    height=th,
                )
            )

            # マッチした領域を塗りつぶして次の検出に備える
            x0 = max(0, max_loc[0] - tw // 2)
            y0 = max(0, max_loc[1] - th // 2)
            x1 = min(result_map.shape[1], max_loc[0] + tw // 2 + 1)
            y1 = min(result_map.shape[0], max_loc[1] + th // 2 + 1)
            result_map[y0:y1, x0:x1] = 0.0

        logger.info(
            "複数マッチング: %s — %d 件検出",
            template_name,
            len(results),
        )
        return results

    def match_multiscale(
        self,
        screen: NDArray[np.uint8],
        template_name: str,
        *,
        scales: tuple[float, ...] = (0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3),
    ) -> MatchResult | None:
        """マルチスケールでテンプレートマッチングを行う.

        Args:
            screen: キャプチャ画像の numpy 配列 (H, W, 3).
            template_name: マッチング対象のテンプレート名.
            scales: 試行するスケールのタプル.

        Returns:
            全スケール中の最高スコアのマッチ結果. 閾値未満の場合は None.
        """
        tmpl = self._templates.get(template_name)
        if tmpl is None:
            logger.warning("テンプレート未登録: %s", template_name)
            return None

        th, tw = tmpl.shape[:2]
        best: MatchResult | None = None

        for scale in scales:
            rw, rh = int(tw * scale), int(th * scale)
            if rw < 5 or rh < 5 or rw > screen.shape[1] or rh > screen.shape[0]:
                continue

            resized = cv2.resize(tmpl, (rw, rh))
            result = cv2.matchTemplate(screen, resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val >= self._threshold and (best is None or max_val > best.score):
                cx = max_loc[0] + rw // 2
                cy = max_loc[1] + rh // 2
                best = MatchResult(
                    template_name=template_name,
                    score=float(max_val),
                    x=cx,
                    y=cy,
                    width=rw,
                    height=rh,
                )

        if best is not None:
            logger.info(
                "マルチスケールマッチング成功: %s score=%.3f pos=(%d,%d)",
                template_name,
                best.score,
                best.x,
                best.y,
            )
        return best
