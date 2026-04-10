# Phase 3: ステートマシン実装

**日時**: 2026-04-10
**対象**: `src/engine/state_machine.py`

## 実装内容

### StateMachine
- SPEC.md の状態遷移表に基づく 8 状態の有限オートマトン
  - IDLE → SEARCHING → SCROLLING → TAPPING_ENEMY → IN_BATTLE → BATTLE_RESULT → DIALOG_HANDLING → ERROR
- メインループ: `start()` → キャプチャ → 状態判定 → ハンドラディスパッチ → sleep
- 各状態ハンドラをメソッドに分離、`_HANDLERS` テーブルでディスパッチ
- スクロール探索: 敵未発見 → swipe → 再探索（max_scroll_retry 回）
- ダイアログ処理: ボタン検出 → タップ → 復帰確認（dialog_retry_count 回で ERROR）
- max_runtime_minutes による自動停止
- start()/stop() による外部制御インターフェース

### テスト (`tests/test_state_machine.py`)
- 14 テストケース（全 pass）
- 正常フロー、スクロール探索、ダイアログ復帰/エラー停止、タイムアウトをカバー
- capture/recognition/control は全て MagicMock

## 検証結果
- pytest: 67 passed, 2 skipped
- mypy: Phase 3 対象ファイルにエラーなし（screen.py の pre-existing issue のみ）

## 備考
- pytest-asyncio をインストール済み
- ハンドラのディスパッチテーブルはモジュールレベル (`_HANDLERS`) に配置し mypy strict 対応
