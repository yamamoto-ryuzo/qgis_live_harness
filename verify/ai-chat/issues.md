# qgis-ai-verify 検証で検出した実装課題

検証実行: 2025 (capability.json updated 参照)。AI-plane は devin_acp / swe-2-high で全項目実施。
issue 管理ツール(dispatcher MCP)が利用不可だったため本ファイルに記録。

## ISSUE-1: geo_import のモーダル exec() が制御チャネルを枯渇させる

- 対象: `plugin.geo_import.action.GeoImport.run`,
  `plugin.geo_import.dialog.GeoImportDialogSettings`,
  `plugin.geo_import.bridge.openSettings`
- 症状: AI-plane でこれらを自然言語実行すると `dlg.exec()` が GUI スレッドを
  占有し、live-driver の `/api/cmd` が応答不能になる(channel dead)。
- 判定: 実装側の問題。bridge/AI 経路から呼ばれる入口は `exec()` ではなく
  非モーダル `show()`(または `open()` + WA_DeleteOnClose)にすべき。
  bridge.py 自体は show/exec を区別する記述があるため、run/openSettings
  経路の exec 使用が不整合。
- 検証上の措置: 3 項目を AI-plane `no_llm` に変更(手動検証項目)。

## ISSUE-2: geo_userfunc `_FunctionEditDialog` が GUI ハングを引き起こす

- 対象: `plugin.geo_userfunc.dialog._FunctionEditDialog`
- 症状: AI 経由で開くと QGIS 全体が無応答になり、プロセス強制終了が必要に
  なった(複数回再現)。
- 判定: 実装側の問題(モーダル再入またはシグナルデッドロックの疑い)。
- 検証上の措置: AI-plane `no_llm` に変更。

## ISSUE-3: 長時間 AI 実行中に QGIS GUI スレッドが飢餓し channel dead になる

- 症状: run_ai.py 実行中、特定項目(上記モーダル系以外でも稀に)で
  `/api/health` は生きているが `/api/cmd`(pyeval)が無応答になる。
  8 連続エラーで runner が abort。
- 観測: セッション再起動で回復。同一項目の再実行では必ずしも再現しない。
- 判定: geo_driver の制御チャネルが GUI スレッド依存で、長時間・高頻度の
  pyeval/screenshot 連打に対する耐性が不足。watchdog/自動再接続の検討余地。
- 対応済み: run_ai.py は 30 項目ごとに ACP セッションをローテート済み。

## ISSUE-4: `live:ensure` の stale セッション probe がタイムアウトする

- 症状: `%USERPROFILE%\.qgis-live\` に死んだセッション JSON が多数残ると、
  probeAll が 180s タイムアウトして既存/新規セッションの確立に失敗する。
- 対応: 検証では `WEBENGINE_LIVE_DIR=test-results/live2` のクリーンな
  ディレクトリで回避。恒久対応として probe の並列化/短縮タイムアウト/
  stale ファイル自動掃除が必要。
- 関連ファイル: `scripts/qgis-session.mjs`

## ISSUE-5: カタログ ID `qgis.action.noname` / `qgis.action.2` の重複・不安定化

- 症状: objectName を持たない QAction(ドック/ツールバーの toggle)が
  `noname` や `2` の id で大量重複登録される。結果ファイル名が衝突し
  (run_ai.py で `#idx` サフィックスを付与して対処)、項目の一意識別が困難。
- 判定: build_catalog/enum_qgis の id 生成が不安定。objectName 空の場合は
  action text / dock title / 親ツールバー名から安定 id を導出すべき。
- 影響: 現状でも出現順ペアリングで動作はするが、セッション間で順序が
  変わると結果が別項目に紐付く危険がある。

## ISSUE-6: 検証コード側の修正(run_ai.py — 今回修正済み)

- 複数行 assert_code が `bool(<code>)` ラップで構文崩壊 → 複数行は
  `result = <code>` 直評価に修正。
- pyeval 名前空間に QAction/QDockWidget/QToolBar が無いセッションで
  assert error 連発 → ASSERT_CODE に import プリリュードを前置。
- AI がツール引数に `\uXXXX` エスケープで日本語を書くと expect regex が
  不一致 → ツール痕跡テキストを `\uXXXX` 実文字化した第2候補にも適用。
- これらは検証ハーネス側の欠陥であり、製品コードの問題ではない。
