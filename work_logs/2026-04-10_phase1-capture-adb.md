# Phase 1 実装: screen capture + ADB controller

**日付:** 2026-04-10  
**対象ブランチ:** master  

## 変更ファイル

### src/control/adb.py — ADB 操作層の実装
- `_base_cmd()`: デバイスシリアル指定時に `-s` オプション付与
- `_run()`: `subprocess.run` による共通実行（タイムアウト・エラーハンドリング付き）
- `_wait_cooldown()`: `time.monotonic()` で前回操作からの経過を計測、`config.yaml` の `tap_cooldown_ms` に対応
- `device_check()`: `adb devices` 出力パース。`device` ステータスのみ接続扱い（`unauthorized` 等は除外）
- `tap(x, y)`: `adb shell input tap` を送信
- `swipe(x1, y1, x2, y2, duration_ms)`: `adb shell input swipe` を送信
- `screencap()`: `adb exec-out screencap -p` で PNG バイト列取得

### src/capture/screen.py — 画面キャプチャ層の実装
- 内部で `AdbController` を保持
- `capture_png_bytes()`: screencap を呼び出し、空データ・例外時に `max_retries` 回リトライ（`retry_delay` 秒間隔）
- `capture()`: PNG → `cv2.imdecode` → BGR numpy ndarray (H, W, 3)

### tests/test_adb.py — ADB テスト (18件)
- `device_check`: 接続/シリアル指定/未接続/unauthorized/タイムアウト
- `tap`: コマンド文字列検証、シリアル付き、失敗時 RuntimeError、タイムアウト
- `swipe`: コマンド文字列検証、デフォルト duration、失敗時 RuntimeError
- `screencap`: 正常系、失敗系
- クールダウン: 連続 tap 時の sleep 動作

### tests/test_capture.py — キャプチャテスト (8件)
- `capture_png_bytes`: 正常取得、空データリトライ、タイムアウトリトライ、リトライ後成功
- `capture`: ndarray 変換成功、デコード失敗時 RuntimeError

## テスト結果

```
26 passed, 2 skipped (integration)
```

## 設計メモ
- `AdbController.screencap()` は生の PNG バイト列を返す単純な実装。リトライロジックは `ScreenCapture` 側に集約。
- クールダウンは `time.monotonic()` ベースで、操作間の最小間隔を保証。
- すべての ADB 呼び出しは `subprocess.run` + `timeout` パラメータで制御。
