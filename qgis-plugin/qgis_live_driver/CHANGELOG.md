# Changelog — qgis_live_driver

このプラグインの変更履歴。Keep a Changelog 準拠。
バージョンは `metadata.txt` の `version` と同期させる。

## [0.7.0] - 2026-10-18

### Added

- **エージェント/スキル(指示書ファイル)**(`ai_client.py`+`ai_panel.py`):
  `~/.qgis-live/agents/*.md` は常時注入の指示書でパネルのコンボで
  選択(複数定義・切替・チャットごとの記憶に対応)。
  `~/.qgis-live/skills/*.md` はオンデマンドの手順書で
  一覧のみプロンプトに載せ、モデルが `qgis_pyeval` の `open()` で
  本文を読む(progressive disclosure)。両者とも「編集」ダイアログ
  (種別コンボでエージェント/スキル切替、編集/表示の2ペイン分割・
  入力中Markdownのライブプレビュー)から作成/編集/削除でき、
  `<plugin>/<kind>/` の同梱デフォルトはユーザ側同名ファイルが優先。
  同梱例として `skills/qgis-basics.md` を追加
- **AI自身による指示書の編集・選択**(`ai_client.py`):
  パネルローカルツール `ai_list_instructions` /
  `ai_read_instruction` / `ai_save_instruction` /
  `ai_delete_instruction` / `ai_select_agent`(保存は常に
  ユーザ側、同梱品は削除不可・同名保存で上書き)。
  エージェント一覧もid+説明+[active]マークでプロンプトに載せ、
  モデルが自律選択可能。保存依頼時は意図からagents/skillsを
  判別して理由を案内する指針をプロンプトに明記。
  外部オーケストレーター向けにMCP/RESTの `qgis_instruction`
  ツール(op=list|read|save|delete)も公開
- **外部MCPサーバ接続(MCPクライアント)**(`ai_client.py`):
  stdlibのみのMCPクライアントを追加。設定は
  `~/.qgis-live/mcp_servers.json`(Claude Desktop互換)、
  `command`=stdio子プロセス / `url`=Streamable HTTP(JSON/SSE両対応、
  Mcp-Session-Id追従)。HTTP側の認証は `headers` 固定値のほか
  `oauth` で authorization_code+PKCE(authorize_url指定時。
  ブラウザ同意→localhostコールバック受信→トークンを
  mcp_tokens.json へ永続化・refresh_token自動更新)と
  client_credentials(token_urlのみ指定時、client_id/secret、
  extraでプロバイダ固有formパラメータ)の両方に対応。
  401で1回リトライ。接続/認証エラー時はアプリ側設定の確認ガイド
  (Redirect URI登録・authorization_code有効・id/secret一致)を表示。
  発見ツールは `mcp_<サーバ>__<ツール>` に
  マングリングしてfunction callingへ混入し、パネルがセッション
  経由でローカル実行。API設定に「MCP」行(状態表示+設定ダイアログ、
  ダイアログには接続例BOXと「例をエディタへ挿入」ボタン付き)、
  保存時に次回送信で再接続。接続失敗はサーバごとに分離して表示
- **運用機能**(`ai_panel.py`+`ai_client.py`):
  実行中の中断ボタン(往復境界で停止)、最後の質問の「再送」、
  ツール実行前の確認モード(チェックONで都度Yes/No)、
  会話履歴のコンテキスト上限(古いターンから切詰め)、
  右下の使用量/累計コスト表示(API応答のusage実測値を
  チャット毎に累積・ctx=直近prompt_tokens実測または文字数推定)、
  チャット履歴の `~/.qgis-live/chats.json` への永続化(最新50件)、
  表示中チャットのMarkdown保存(↓)と履歴削除(✕)

### Changed

- API設定の表示切替トグルを⚙アイコンボタンに簡略化

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
