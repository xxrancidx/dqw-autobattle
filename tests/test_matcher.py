"""テンプレートマッチングのテスト."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from numpy.typing import NDArray

from src.recognition.matcher import MatchResult, TemplateMatcher


class TestMatchResult:
    """MatchResult データクラスのテスト."""

    def test_create(self) -> None:
        """MatchResult の生成."""
        result = MatchResult(
            template_name="test",
            score=0.95,
            x=100,
            y=200,
            width=50,
            height=50,
        )
        assert result.score == 0.95
        assert result.x == 100


class TestTemplateMatcher:
    """TemplateMatcher のテスト."""

    def test_init(self, templates_dir: Path) -> None:
        """初期化テスト."""
        tm = TemplateMatcher(templates_dir=templates_dir, threshold=0.9)
        assert tm._threshold == 0.9

    def test_load_templates_not_implemented(self, matcher: TemplateMatcher) -> None:
        """load_templates() が NotImplementedError を送出する."""
        with pytest.raises(NotImplementedError):
            matcher.load_templates()

    def test_match_not_implemented(
        self, matcher: TemplateMatcher, sample_screen: NDArray[np.uint8]
    ) -> None:
        """match() が NotImplementedError を送出する."""
        with pytest.raises(NotImplementedError):
            matcher.match(sample_screen, "test_template")
