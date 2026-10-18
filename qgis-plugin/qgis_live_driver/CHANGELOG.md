# Changelog — qgis_live_driver

このプラグインの変更履歴。Keep a Changelog 準拠。
バージョンは `metadata.txt` の `version` と同期させる。

## [0.5.0] - 2026-10-18

### Added

- **汎用ブリッジ `_GenericBridge`**(`live_driver.py`): `plugin.bridge` を
  持たないプラグインに `bridge_call` が自動フォールバックする共通制御面。
  `pluginInfo`/`status`/`actions`/`trigger`/`run`/`openDialog`/
  `closeDialog` を提供し、`run`/`trigger` は QTimer.singleShot(0) で
  非同期発火するため対象がmodalダイアログを開いてもコマンド応答は
  ブロックされない。サードパーティ製プラグイン(mmqgis等)も
  repo外改変なしでAIから操作できる
- `describe_plugins` がbridge未搭載プラグインにも汎用アダプタ経由の
  metadata由来の自己記述を載せる(`generic: true` フラグ付き)。
  全ロード済みプラグインがカタログ上で発見・操作可能になった
- `bridge.py`(`QgisLiveBridge`)を新設しドライバ自身の `plugin.bridge`
  に配線。`pluginInfo`/`status` でコマンド面と稼働状態を自己記述

## [0.4.0] - 2026-10-18

### Added

- `describe_plugins` コマンドを追加。ロード済み全プラグインを列挙し、
  `bridge` を持つプラグインは各 `pluginInfo()` の自己記述
  (id/name/summary/when_to_use/invoke/methods/state)を集約した
  AI向けカタログを返す。`status` のプラグイン情報に `bridge`
  フラグも追加
- `mcp_http.py` / `mcp_stdio.py` のTOOLSに `qgis_describe_plugins`
  を追加(REST `/api/tools`・MCP `/mcp`・stdio shim全面で公開)

## [0.3.0] - 2026-10-18

### Added

- **AIアシスタントパネル**(`ai_panel.py` + `ai_client.py`)。
  `プラグイン > QGIS Live Driver > AI アシスタント` で開くチャット型
  エージェントドック。OpenAI互換(`/chat/completions` + function
  calling)とGemini(`generateContent` + functionDeclarations)を接続し、
  `mcp_http.TOOLS` と同じツール群を `driver.submit()` 経由でループ実行。
  リモート制御OFF時はパネル専用内部ドライバで動作
- APIキーはOS資格情報ストアに保存(`credential_store.py`:
  Windows=DPAPI / macOS=キーチェーン / Linux=Secret Service、
  フォールバックは600権限ファイル)
- モデル欄は編集可コンボ+「取得」ボタンで `GET {base}/models` から
  モデル一覧を取込み(種別グルーピング+価格表示)

## [0.2.0] - 2026-10-18

### Added

- 公開向けハードニング。HTTP REST `/api/*`・MCP Streamable HTTP
  `/mcp`・同梱stdio shim(`mcp_stdio.py`)の3接続面を追加し、
  ファイルJSONLと同じdispatchへ統合
- 全チャネルでセッショントークン認証を必須化(live_dir/token・
  レジストリJSONともユーザ限定ACL)。`QGIS_LIVE_API_KEY` /
  `QGIS_LIVE_TOOLS` envで公開範囲を制御
- ハブコマンド追加: `status` / `open_plugin` / `reload_plugin` /
  `bridge_call` + `plugin_id` 転送(`reply`注入で呼出元へ結果返却)

## [0.1.0] - 2026-10-18

### Added

- 初版。WebEngineを持たない制御専用プラグインとして、
  `WEBENGINE_LIVE_DIR/qgis-<pid>/<plugin_id>/` の
  commands.jsonl/results.jsonl ファイル経由で `pyeval` /
  `screenshot` を提供
