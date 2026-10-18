# Changelog — qgis_live_driver

このプラグインの変更履歴。Keep a Changelog 準拠。
バージョンは `metadata.txt` の `version` と同期させる。

## [0.6.0] - 2026-10-18

### Added

- **AIアシスタントに GitHub Copilot プロバイダを追加**(`ai_client.py` の
  `CopilotProvider`)。メッセージ形式はOpenAI互換だが、認証はAPIキー欄の
  GitHubトークン(`gho_`/`ghu_`/`ghp_`…)を
  `api.github.com/copilot_internal/v2/token` で短期トークンに交換し、
  応答の `endpoints.api`(individual/business/enterprise)へ送る
  (トークンは期限切れ前までキャッシュ)。**対応プランは
  Pro/Free/Business/Enterprise/EMU** — Business/Enterprise/EMUでは
  `endpoints.api` がプラン別API先を返すため同じ経路で自動解決
  (EMUのPAT制限時はデバイスフローを利用)。`v2/token` が応答しない環境では
  `copilot_internal/user` でAPI先を解決しGitHubトークンをそのまま
  Bearerに使う(`@github/copilot` CLI方式)フォールバック付き。
  GitHub Copilotの契約が必要で、エンドポイントはVS Codeの
  Copilot Chatと同じ内部APIを使う点に注意
- **「GitHubでサインイン」ボタン**(`ai_panel.py`): copilot選択時のみ
  表示され、OAuthデバイスフローでGitHubトークンを取得してAPIキー欄と
  OS資格情報ストアへ保存。既定のclient_idはVS Codeの公開OAuth Appで、
  同意画面には「Visual Studio Code」と表示される。
  `QGIS_LIVE_GITHUB_CLIENT_ID` で独自OAuth Appに差し替え可
- Copilotの `GET {api}/models` 応答(`capabilities.type`/`policy.state`/
  `supports.vision`/`limits.max_context_window_tokens`)をパネルの
  モデル一覧(種別・コンテキスト長付き)にマッピング
- エンドポイントを既定から変更した場合はトークン交換せずGitHubトークンを
  そのままBearerに使うため、copilot-api等の互換プロキシにも接続可能
- **AI応答のMarkdownレンダリング**(`ai_panel.py`): アシスタントの
  メッセージを `QTextDocument.setMarkdown()` で変換して表示し、
  見出し・リスト・表・コードブロックが整形される。
  user/tool/error表示は従来通りエスケープ済みテキスト
- **チャット履歴**(`ai_panel.py`): 「新しいチャット」ボタンで現在の
  会話を履歴コンボへ保存し新規開始(コンテキストもリセット)。
  履歴コンボから過去チャットを選ぶと表示内容と会話コンテキストが
  復元され、そのまま会話を継続できる。セッションはQGIS起動中のみ
  メモリ保持(永続化はしない)
- **ドックのタブ化**(`ai_panel.py`): パネル追加時に同じドック領域へ
  表示中ドックがあれば `tabifyDockWidget` でタブ化し、
  縦分割せずレイヤパネル等とタブで重なる(QGISプラグインの標準的な
  振る舞い)
- **API設定の表示切替**(`ai_panel.py`): 「新しいチャット」左の
  「設定」トグルボタンでAPI設定ボックスを表示/非表示。
  状態はQSettingsに保存。初回はAPIキー未設定時のみ開く

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
