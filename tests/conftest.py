"""共通テストフィクスチャ."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest
from numpy.typing import NDArray

from src.capture.screen import ScreenCapture
from src.control.adb import AdbController
from src.recognition.matcher import TemplateMatcher


@pytest.fixture()
def sample_screen() -> NDArray[np.uint8]:
    """テスト用のダミー画面画像（1080x2400 BGR）."""
    return np.zeros((2400, 1080, 3), dtype=np.uint8)


@pytest.fixture()
def templates_dir(tmp_path: Path) -> Path:
    """テスト用テンプレートディレクトリ."""
    d = tmp_path / "templates"
    d.mkdir()
    return d


@pytest.fixture()
def mock_capture() -> ScreenCapture:
    """モック化された ScreenCapture."""
    return MagicMock(spec=ScreenCapture)


@pytest.fixture()
def mock_controller() -> AdbController:
    """モック化された AdbController."""
    return MagicMock(spec=AdbController)


@pytest.fixture()
def matcher(templates_dir: Path) -> TemplateMatcher:
    """テスト用 TemplateMatcher."""
    return TemplateMatcher(templates_dir=templates_dir)
