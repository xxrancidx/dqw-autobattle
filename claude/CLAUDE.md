# DQW AutoBattle System

scrcpy + ADB でミラーリングした Pixel 8 上の「ドラゴンクエストウォーク」を画像認識で自動操作するシステム。

## Tech Stack

- Python 3.11+, OpenCV, FastAPI, uvicorn
- ADB (Android Debug Bridge) で端末制御
- テンプレートマッチングで画面状態を認識

## Key Directories

- `src/capture/` — ADB screencap による画面取得
- `src/recognition/` — OpenCV テンプレートマッチング・状態判定
- `src/control/` — ADB tap/swipe コマンド送信
- `src/engine/` — ステートマシン（メインループ）
- `src/dashboard/` — FastAPI + WebSocket 監視 UI
- `templates/` — マッチング用テンプレート画像（PNG）
- `tests/fixtures/` — テスト用スクリーンショット

## Commands

- テスト: `pytest tests/ -v`
- Lint: `ruff check src/ tests/`
- Format: `ruff format src/ tests/`
- 型チェック: `mypy src/`
- 実行: `python -m src.main`
- ダッシュボード単体: `uvicorn src.dashboard.app:app --reload --port 8080`

## Code Style

- 型ヒント必須（全関数・メソッド）
- docstring は Google スタイル
- import は isort 準拠（標準ライブラリ → サードパーティ → ローカル）
- クラスより関数を優先。状態が必要な場合のみクラスを使う
- 設定値のハードコードは禁止。すべて config.yaml から読み込む

## Architecture Rules

- 各層（capture / recognition / control / engine）は疎結合に保つ
- 層間のやり取りはデータクラス or TypedDict で型付けする
- ADB コマンドは `src/control/adb.py` に集約。他モジュールから直接 subprocess を呼ばない
- ステートマシンの状態遷移は `src/engine/state_machine.py` の Enum で管理
- ログは Python 標準 logging + structlog。print デバッグ禁止

## Testing

- テストファイルは `tests/test_{module}.py` の命名規則
- ADB 依存のテストは `@pytest.mark.integration` でマーク
- テンプレートマッチングのテストは `tests/fixtures/` のスクリーンショットを使う
- モックは `unittest.mock.patch` で ADB subprocess をモック

## Gotchas

- Pixel 8 の解像度は 1080x2400。テンプレート画像もこの解像度で作成する
- `adb exec-out screencap -p` は稀にバイナリが壊れる。リトライロジック必須
- DQW のフィールド画面は 3D でカメラアングルが変わるため、敵シンボルのテンプレートは複数サイズ用意する
- config.yaml 変更時はダッシュボードからホットリロード可能にする
