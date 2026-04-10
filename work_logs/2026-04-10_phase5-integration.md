# Phase 5: main.py 完成・全コンポーネント結合

**日時:** 2026-04-10  
**ステータス:** 完了

## 実装内容

### 1. src/logging/logger.py — setup_logging() 実装
- `RotatingFileHandler` でファイル出力（10MB ローテーション、5世代保持）
- `StreamHandler` でコンソール出力
- `WebSocketLogHandler` でキューベースの WS 配信用ログ蓄積
- `structlog` の configure 設定（stdlib 連携）
- `get_ws_handler()` シングルトンアクセサ

### 2. src/engine/state_machine.py — イベントシステム追加
- `EventCallback` 型定義（async コールバック）
- `add_event_callback()` / `_emit_event()` で各 tick 後に status イベント配信
- `last_screen` プロパティ追加（プレビュー配信・エラースクリーンショット用）

### 3. src/dashboard/app.py — StateMachine 統合
- `set_state_machine()` で外部から StateMachine を注入
- StateMachine 未注入時はテスト互換モード（従来の `_system_state` 辞書ベース）
- `/api/start` `/api/stop` が実際の StateMachine を制御
- `_log_queue_to_ws()` — WebSocketLogHandler キュー → `/ws/logs` 配信
- `_preview_to_ws()` — 最新キャプチャを Base64 で `/ws/preview` 配信
- `on_event` → `lifespan` パターンに移行（DeprecationWarning 解消）

### 4. src/main.py — 全コンポーネント結合
- 初期化チェーン: AdbController → ScreenCapture → TemplateMatcher → StateDetector → StateMachine
- config.yaml から全パラメータ読み込み
- FastAPI ダッシュボードを `threading.Thread(daemon=True)` で別スレッド起動
- StateMachine イベントコールバックで WS 配信 + エラースクリーンショット保存
- Ctrl+C グレースフルシャットダウン（Windows 対応の signal handler）

### 5. エラースクリーンショット自動保存
- ERROR 遷移時に `logs/screenshots/error_YYYYMMDD_HHMMSS.png` として保存
- 直近100枚を保持（古いものから自動削除）

## 品質チェック結果
- `ruff check src/ tests/` — All checks passed!
- `mypy src/` — Success: no issues found in 16 source files
- `pytest tests/ -v` — 90 passed, 2 skipped

## 変更ファイル
- src/logging/logger.py（実装完了）
- src/engine/state_machine.py（イベントシステム追加）
- src/dashboard/app.py（StateMachine 統合 + lifespan 移行）
- src/main.py（全コンポーネント結合）
- src/control/adb.py（ruff 修正: 行長、nested if）
- src/capture/screen.py（mypy 修正: 戻り値型）
- tests/test_logger.py（実装に合わせたテスト書き換え）
- tests/test_dashboard.py（_state_machine リセット追加、未使用 import 削除）
- tests/test_capture.py（nested with 修正）
- tests/test_adb.py, tests/test_state_machine.py（import 並び順修正）
