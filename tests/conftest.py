"""共通テストフィクスチャ."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import cv2
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


def create_template_image(
    width: int = 60,
    height: int = 60,
    color: tuple[int, int, int] = (0, 200, 0),
) -> NDArray[np.uint8]:
    """テスト用テンプレート画像を生成する."""
    img = np.full((height, width, 3), color, dtype=np.uint8)
    # 識別しやすいように十字パターンを描画
    cv2.line(img, (width // 2, 0), (width // 2, height), (255, 255, 255), 2)
    cv2.line(img, (0, height // 2), (width, height // 2), (255, 255, 255), 2)
    return img


def embed_template(
    screen: NDArray[np.uint8],
    template: NDArray[np.uint8],
    x: int,
    y: int,
) -> NDArray[np.uint8]:
    """画面画像にテンプレートを埋め込む（コピーを返す）."""
    out = screen.copy()
    th, tw = template.shape[:2]
    out[y : y + th, x : x + tw] = template
    return out


def save_template(templates_dir: Path, name: str, img: NDArray[np.uint8]) -> Path:
    """テンプレート画像をディレクトリに保存する."""
    path = templates_dir / f"{name}.png"
    _, buf = cv2.imencode(".png", img)
    buf.tofile(str(path))
    return path
