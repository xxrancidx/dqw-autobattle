"""テンプレートマッチングのテスト."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from numpy.typing import NDArray

from src.recognition.matcher import MatchResult, TemplateMatcher
from tests.conftest import create_template_image, embed_template, save_template


class TestMatchResult:
    """MatchResult データクラスのテスト."""

    def test_create(self) -> None:
        result = MatchResult(
            template_name="test", score=0.95, x=100, y=200, width=50, height=50
        )
        assert result.score == 0.95
        assert result.x == 100
        assert result.template_name == "test"

    def test_frozen(self) -> None:
        result = MatchResult(
            template_name="test", score=0.9, x=0, y=0, width=10, height=10
        )
        with pytest.raises(AttributeError):
            result.score = 0.5  # type: ignore[misc]


class TestTemplateMatcher:
    """TemplateMatcher のテスト."""

    def test_init(self, templates_dir: Path) -> None:
        tm = TemplateMatcher(templates_dir=templates_dir, threshold=0.9)
        assert tm._threshold == 0.9

    def test_load_templates_empty_dir(self, matcher: TemplateMatcher) -> None:
        """空ディレクトリからの読み込みでエラーにならない."""
        matcher.load_templates()
        assert len(matcher._templates) == 0

    def test_load_templates_missing_dir(self, tmp_path: Path) -> None:
        """存在しないディレクトリで FileNotFoundError."""
        tm = TemplateMatcher(templates_dir=tmp_path / "nonexistent")
        with pytest.raises(FileNotFoundError):
            tm.load_templates()

    def test_load_templates_reads_png(self, templates_dir: Path) -> None:
        """PNG ファイルを読み込みテンプレートとして登録する."""
        tmpl = create_template_image(40, 40, (100, 100, 100))
        save_template(templates_dir, "btn_ok", tmpl)
        save_template(templates_dir, "btn_cancel", tmpl)

        matcher = TemplateMatcher(templates_dir=templates_dir)
        matcher.load_templates()
        assert "btn_ok" in matcher._templates
        assert "btn_cancel" in matcher._templates

    def test_match_success(
        self, templates_dir: Path, sample_screen: NDArray[np.uint8]
    ) -> None:
        """テンプレートが画面内に存在する場合にマッチする."""
        tmpl = create_template_image(60, 60, (0, 200, 0))
        save_template(templates_dir, "target", tmpl)

        screen = embed_template(sample_screen, tmpl, x=500, y=1200)

        matcher = TemplateMatcher(templates_dir=templates_dir, threshold=0.8)
        matcher.load_templates()

        result = matcher.match(screen, "target")
        assert result is not None
        assert result.template_name == "target"
        assert result.score >= 0.8
        # 中心座標が埋め込み位置付近にある
        assert abs(result.x - (500 + 30)) <= 2
        assert abs(result.y - (1200 + 30)) <= 2

    def test_match_no_hit(
        self, templates_dir: Path, sample_screen: NDArray[np.uint8]
    ) -> None:
        """テンプレートが画面内に存在しない場合に None を返す."""
        tmpl = create_template_image(60, 60, (0, 200, 0))
        save_template(templates_dir, "target", tmpl)

        # 黒一色の画面にはマッチしない
        matcher = TemplateMatcher(templates_dir=templates_dir, threshold=0.8)
        matcher.load_templates()

        result = matcher.match(sample_screen, "target")
        assert result is None

    def test_match_unknown_template(
        self, templates_dir: Path, sample_screen: NDArray[np.uint8]
    ) -> None:
        """未登録テンプレートで None を返す."""
        matcher = TemplateMatcher(templates_dir=templates_dir)
        matcher.load_templates()

        result = matcher.match(sample_screen, "nonexistent")
        assert result is None

    def test_match_any_best_score(
        self, templates_dir: Path, sample_screen: NDArray[np.uint8]
    ) -> None:
        """match_any は最もスコアの高い結果を返す."""
        tmpl_a = create_template_image(50, 50, (255, 0, 0))
        tmpl_b = create_template_image(50, 50, (0, 0, 255))
        save_template(templates_dir, "a", tmpl_a)
        save_template(templates_dir, "b", tmpl_b)

        # b だけ埋め込む
        screen = embed_template(sample_screen, tmpl_b, x=300, y=800)

        matcher = TemplateMatcher(templates_dir=templates_dir, threshold=0.8)
        matcher.load_templates()

        result = matcher.match_any(screen, ["a", "b"])
        assert result is not None
        assert result.template_name == "b"

    def test_match_any_no_hit(
        self, templates_dir: Path, sample_screen: NDArray[np.uint8]
    ) -> None:
        """match_any で全テンプレートが閾値未満なら None."""
        tmpl = create_template_image(50, 50, (255, 0, 0))
        save_template(templates_dir, "x", tmpl)

        matcher = TemplateMatcher(templates_dir=templates_dir, threshold=0.8)
        matcher.load_templates()

        result = matcher.match_any(sample_screen, ["x"])
        assert result is None

    def test_match_multi(
        self, templates_dir: Path, sample_screen: NDArray[np.uint8]
    ) -> None:
        """match_multi で複数の同一テンプレートを検出する."""
        tmpl = create_template_image(40, 40, (0, 255, 255))
        save_template(templates_dir, "enemy", tmpl)

        # 2 箇所に埋め込む（十分離す）
        screen = embed_template(sample_screen, tmpl, x=100, y=200)
        screen = embed_template(screen, tmpl, x=600, y=1500)

        matcher = TemplateMatcher(templates_dir=templates_dir, threshold=0.8)
        matcher.load_templates()

        results = matcher.match_multi(screen, "enemy")
        assert len(results) >= 2
        for r in results:
            assert r.template_name == "enemy"
            assert r.score >= 0.8

    def test_match_multi_no_hit(
        self, templates_dir: Path, sample_screen: NDArray[np.uint8]
    ) -> None:
        """match_multi でマッチなしなら空リスト."""
        tmpl = create_template_image(40, 40, (0, 255, 255))
        save_template(templates_dir, "enemy", tmpl)

        matcher = TemplateMatcher(templates_dir=templates_dir, threshold=0.8)
        matcher.load_templates()

        results = matcher.match_multi(sample_screen, "enemy")
        assert results == []

    def test_match_multi_unknown_template(
        self, templates_dir: Path, sample_screen: NDArray[np.uint8]
    ) -> None:
        """match_multi で未登録テンプレートなら空リスト."""
        matcher = TemplateMatcher(templates_dir=templates_dir)
        matcher.load_templates()

        results = matcher.match_multi(sample_screen, "nonexistent")
        assert results == []
