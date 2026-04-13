"""画面状態判定のテスト."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from numpy.typing import NDArray

from src.recognition.detector import ScreenState, StateDetector
from src.recognition.matcher import TemplateMatcher
from tests.conftest import create_template_image, embed_template, save_template


class TestScreenState:
    """ScreenState Enum のテスト."""

    def test_states_exist(self) -> None:
        assert ScreenState.FIELD is not None
        assert ScreenState.BATTLE is not None
        assert ScreenState.BATTLE_RESULT is not None
        assert ScreenState.DIALOG is not None
        assert ScreenState.WALK_MODE_ON is not None
        assert ScreenState.WALK_MODE_OFF is not None
        assert ScreenState.ENEMY_SYMBOL is not None
        assert ScreenState.UNKNOWN is not None


class TestStateDetector:
    """StateDetector のテスト."""

    @pytest.fixture()
    def _setup_templates(self, templates_dir: Path) -> dict[str, NDArray[np.uint8]]:
        """各状態用のテンプレートを生成・保存."""
        templates: dict[str, NDArray[np.uint8]] = {}
        colors: dict[str, tuple[int, int, int]] = {
            "dialog_ok": (255, 0, 0),
            "dialog_close": (255, 50, 0),
            "battle_result": (0, 255, 0),
            "battle_attack": (0, 0, 255),
            "battle_command": (0, 0, 200),
            "walk_mode_on": (255, 255, 0),
            "walk_mode_off": (255, 0, 255),
            "field_menu": (0, 255, 255),
            "field_map": (128, 128, 128),
            "enemy_symbol": (47, 134, 220),  # BGR orange (HSV H=15)
        }
        for name, color in colors.items():
            img = create_template_image(50, 50, color)
            save_template(templates_dir, name, img)
            templates[name] = img
        return templates

    def _make_detector(self, templates_dir: Path) -> StateDetector:
        matcher = TemplateMatcher(templates_dir=templates_dir, threshold=0.8)
        matcher.load_templates()
        return StateDetector(matcher=matcher)

    def test_detect_dialog(
        self,
        templates_dir: Path,
        sample_screen: NDArray[np.uint8],
        _setup_templates: dict[str, NDArray[np.uint8]],
    ) -> None:
        """DIALOG 状態を正しく検出する."""
        screen = embed_template(
            sample_screen, _setup_templates["dialog_ok"], x=400, y=1500
        )
        detector = self._make_detector(templates_dir)
        assert detector.detect(screen) == ScreenState.DIALOG

    def test_detect_battle(
        self,
        templates_dir: Path,
        sample_screen: NDArray[np.uint8],
        _setup_templates: dict[str, NDArray[np.uint8]],
    ) -> None:
        """BATTLE 状態を正しく検出する."""
        screen = embed_template(
            sample_screen, _setup_templates["battle_attack"], x=300, y=1000
        )
        detector = self._make_detector(templates_dir)
        assert detector.detect(screen) == ScreenState.BATTLE

    def test_detect_battle_result(
        self,
        templates_dir: Path,
        sample_screen: NDArray[np.uint8],
        _setup_templates: dict[str, NDArray[np.uint8]],
    ) -> None:
        """BATTLE_RESULT 状態を正しく検出する."""
        screen = embed_template(
            sample_screen, _setup_templates["battle_result"], x=200, y=600
        )
        detector = self._make_detector(templates_dir)
        assert detector.detect(screen) == ScreenState.BATTLE_RESULT

    def test_detect_field(
        self,
        templates_dir: Path,
        sample_screen: NDArray[np.uint8],
        _setup_templates: dict[str, NDArray[np.uint8]],
    ) -> None:
        """FIELD 状態を正しく検出する."""
        screen = embed_template(
            sample_screen, _setup_templates["field_menu"], x=900, y=2200
        )
        detector = self._make_detector(templates_dir)
        assert detector.detect(screen) == ScreenState.FIELD

    def test_detect_walk_mode_on(
        self,
        templates_dir: Path,
        sample_screen: NDArray[np.uint8],
        _setup_templates: dict[str, NDArray[np.uint8]],
    ) -> None:
        """WALK_MODE_ON 状態を正しく検出する."""
        screen = embed_template(
            sample_screen, _setup_templates["walk_mode_on"], x=500, y=800
        )
        detector = self._make_detector(templates_dir)
        assert detector.detect(screen) == ScreenState.WALK_MODE_ON

    def test_detect_unknown(
        self,
        templates_dir: Path,
        sample_screen: NDArray[np.uint8],
        _setup_templates: dict[str, NDArray[np.uint8]],
    ) -> None:
        """何もマッチしない場合に UNKNOWN を返す."""
        detector = self._make_detector(templates_dir)
        assert detector.detect(sample_screen) == ScreenState.UNKNOWN

    def test_dialog_priority_over_field(
        self,
        templates_dir: Path,
        sample_screen: NDArray[np.uint8],
        _setup_templates: dict[str, NDArray[np.uint8]],
    ) -> None:
        """DIALOG は FIELD より優先度が高い."""
        screen = embed_template(
            sample_screen, _setup_templates["field_menu"], x=900, y=2200
        )
        screen = embed_template(screen, _setup_templates["dialog_ok"], x=400, y=1500)
        detector = self._make_detector(templates_dir)
        assert detector.detect(screen) == ScreenState.DIALOG

    def test_find_enemy(
        self,
        templates_dir: Path,
        sample_screen: NDArray[np.uint8],
        _setup_templates: dict[str, NDArray[np.uint8]],
    ) -> None:
        """find_enemy で敵シンボルを検出する."""
        screen = embed_template(
            sample_screen, _setup_templates["enemy_symbol"], x=300, y=700
        )
        detector = self._make_detector(templates_dir)
        result = detector.find_enemy(screen)
        assert result is not None
        assert result.template_name == "enemy_symbol"

    def test_find_enemy_none(
        self,
        templates_dir: Path,
        sample_screen: NDArray[np.uint8],
        _setup_templates: dict[str, NDArray[np.uint8]],
    ) -> None:
        """敵シンボルがない場合に None を返す."""
        detector = self._make_detector(templates_dir)
        assert detector.find_enemy(sample_screen) is None

    def test_find_enemies_multi(
        self,
        templates_dir: Path,
        sample_screen: NDArray[np.uint8],
        _setup_templates: dict[str, NDArray[np.uint8]],
    ) -> None:
        """find_enemies で複数の敵シンボルを検出する."""
        tmpl = _setup_templates["enemy_symbol"]
        screen = embed_template(sample_screen, tmpl, x=100, y=300)
        screen = embed_template(screen, tmpl, x=700, y=1800)

        detector = self._make_detector(templates_dir)
        results = detector.find_enemies(screen)
        assert len(results) >= 2

    def test_find_dialog_button(
        self,
        templates_dir: Path,
        sample_screen: NDArray[np.uint8],
        _setup_templates: dict[str, NDArray[np.uint8]],
    ) -> None:
        """find_dialog_button でダイアログボタンを検出する."""
        screen = embed_template(
            sample_screen, _setup_templates["dialog_ok"], x=500, y=1400
        )
        detector = self._make_detector(templates_dir)
        result = detector.find_dialog_button(screen)
        assert result is not None
        assert result.template_name == "dialog_ok"

    def test_find_dialog_button_none(
        self,
        templates_dir: Path,
        sample_screen: NDArray[np.uint8],
        _setup_templates: dict[str, NDArray[np.uint8]],
    ) -> None:
        """ダイアログボタンがない場合に None を返す."""
        detector = self._make_detector(templates_dir)
        assert detector.find_dialog_button(sample_screen) is None
