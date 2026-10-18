# QGIS Live Driver (`qgis_live_driver`)

実行中のQGISプロセスを**同じPC上のクライアント(AIツール等)から遠隔操作**するための、
UIを持たない制御専用プラグイン。
`python/plugins/` へのコピーだけで任意のQGISインストールに単独導入できる
(リポジトリ・Node不要)。

このプラグインは `QWebEngineView` を持たないため、
**WebEngineを使わない任意のQGIS環境・任意の他プラグイン**に対しても
`pyeval` 経由の遠隔操作面を提供できる。

- コマンド: `pyeval`(任意Python実行) / `screenshot` / `status` /
  `open_plugin` / `reload_plugin` / `bridge_call` + `plugin_id` 転送(hub)
- 接続面(4系統・全て同じdispatchへ): ファイルJSONL /
  HTTP REST `/api/*` / MCP Streamable HTTP `/mcp` / MCP stdio (`mcp_stdio.py`)

**詳細ドキュメント(コマンド一覧・制御範囲・RESTエンドポイント等):**
https://yamamoto-ryuzo.github.io/qgis_live_harness/driver.html

## 有効化

```powershell
# このリポジトリから(全プラグイン一括deploy)
powershell -ExecutionPolicy Bypass -File scripts/deploy-plugin.ps1 -Copy

# または手動: このフォルダを python/plugins/qgis_live_driver/ へコピーし、
# QGISのプラグイン管理で有効化
```

有効化は2経路(既定ではOFF・無害):

- **メニュートグル**: `プラグイン > QGIS Live Driver > リモート制御 (localhostのみ)`。
  初回ON時に警告ダイアログを表示し、QSettingsに保存されるため次回起動から自動有効。
- **環境変数**: `WEBENGINE_LIVE_DIR` 設定時は起動時に即座に有効(開発用途。
  `scripts/verify-in-qgis.ps1` が付与して起動する)。

## AI アシスタントパネル

`プラグイン > QGIS Live Driver > AI アシスタント` で、
**LLM APIを接続してQGISを対話操作するチャットドック**を開ける
(`ai_panel.py` + `ai_client.py`)。

- **プロバイダ**(コンボで選択。設定はプロバイダごとに別保存):
  - **OpenAI互換**: Chat Completions
    (`POST {base}/chat/completions` + function calling)。
    エンドポイントを変えれば Ollama (`http://localhost:11434/v1`)・
    LM Studio・OpenRouter等のローカル/互換サーバも使える
  - **Gemini**: Google Gemini API
    (`POST {base}/models/{model}:generateContent` +
    functionDeclarations、認証は `x-goog-api-key`)。
    APIキーは AI Studio で発行。既定モデル `gemini-2.5-flash`
  - **GitHub Copilot**: OpenAI互換のCopilot API
    (`POST {api}/chat/completions`)。**GitHub Copilotの契約が必要**。
    APIキー欄にはGitHubトークン(`gho_`/`ghu_`/`ghp_`…)を入れる。
    内部で `api.github.com/copilot_internal/v2/token` に交換し、
    応答の `endpoints.api` (individual/business/enterprise)へ送る。
    `v2/token` が応答しない環境では `copilot_internal/user` で
    API先だけを解決しGitHubトークンをそのままBearerに使う
    (`@github/copilot` CLIと同じ動作)に自動フォールバック。
    **「GitHubでサインイン」ボタン**でOAuthデバイスフローによる
    トークン取得もできる(既定のclient_idはVS Codeの公開OAuth App。
    `QGIS_LIVE_GITHUB_CLIENT_ID` で差し替え可)。
    エンドポイントを既定から変えた場合はトークン交換せず
    GitHubトークンをそのままBearerに使うため、
    copilot-api等の互換プロキシにも繋がる。
    **対応プラン**: Pro/Free/Business/Enterprise/EMU
    (Enterprise Managed Users。EMUはエンタープライズから
    Business/Enterpriseシートを付与された場合に使える)。
    Business/Enterprise/EMUでは `endpoints.api` が
    `api.business.`/`api.enterprise.githubcopilot.com` を返すため
    同じ経路で自動解決される。EMUではPAT発行が企業ポリシーで
    制限されうるため「GitHubでサインイン」(デバイスフロー)推奨。
    組織のCopilotモデルポリシーで無効化されたモデルは
    一覧・使用とも不可。IdP条件付きアクセス等の企業側制限は
    アプリ側では回避不可
- **モデル選択**: モデル欄は編集可コンボ。隣の「取得」ボタンで
  `GET {base}/models` から利用可能モデル一覧を取り込める
  (GeminiではgenerateContent非対応モデルを除外)。
  一覧は種別(テキスト/画像入力可・画像生成・埋め込み等)で
  グループ化され、各項目に価格(入力/出力, $/1Mトークン)を併記。
  価格はOpenRouter等が返す `pricing`/`modality`/`context_length`
  を優先し、無ければ主要モデルの既知価格表(参考値)を使う。
  既定エンドポイント利用時は「取得」前から推奨モデル一覧を表示。
  モデル欄の下に選択中モデルの種別・価格・コンテキスト長も出る
- **表示**: AI応答はMarkdownレンダリング(見出し/リスト/表/
  コードブロック)。「新しいチャット」で現在の会話を履歴コンボへ
  保存して新規開始。履歴コンボから過去チャットを開くと
  表示とコンテキストが復元され会話を継続できる(QGIS起動中のみ保持)
- **ツール**: `mcp_http.TOOLS` と同じセット
  (`qgis_pyeval` / `qgis_screenshot` / `qgis_status` /
  `qgis_eval` / `qgis_devreload` / `qgis_open_plugin` /
  `qgis_reload_plugin` / `qgis_bridge_call`)をモデルに渡し、
  戻ってきたtool_callを `driver.submit()` で実行して結果を返す
  エージェントループ(上限25往復)
- **リモート制御トグルOFFでも動く**: パネル専用の内部LiveDriver
  (レジストリ・HTTP公開面なし)を使うため、外部公開を有効化せずに
  AI操作だけを試せる
- **vision**: 「スクリーンショットを画像として送信」をONにすると
  `qgis_screenshot` の結果を `image_url` contentでモデルに返す
  (非対応モデルではAPIエラーになるのでOFFに)
- 設定(エンドポイント/モデル)はQSettingsに保存。
  **APIキーはOSの資格情報ストアに保存**(`credential_store.py`):
  WindowsはDPAPI(ブラウザのパスワード保存と同じユーザ紐付け暗号化)、
  macOSはキーチェーン、LinuxはSecret Service(secret-tool)。
  いずれも無い環境のみ `~/.qgis-live/ai-secrets.json`(600権限・平文)に
  フォールバック。パネルの「キー保存先」欄で現バックエンドを確認できる。
  **ストア書込み自体に失敗した場合はエラー表示し、平文では保存しない**

## セキュリティモデル(localhost限定)

`pyeval` は **任意コード実行** のため、全チャネルを以下で保護する:

- **127.0.0.1 バインドのみ** — 外部ネットワークからは到達不能
- **セッショントークン必須** — 起動ごとに自動生成。HTTPは
  `Authorization: Bearer` 等、commands.jsonl は各行の `token` フィールドで照合。
  トークンは `~/.qgis-live/<pid>-qgis_live_driver.json` (レジストリ)と
  `live_dir/token` にのみ書き出され、ユーザ限定ACLを適用
- **Host/Origin 検証** — HostまたはOriginがloopback以外を指すHTTP要求は拒否
  (DNSリバインド・ブラウザ経由のドライブバイ対策)
- `QGIS_LIVE_TOOLS` で公開コマンド種別を絞れる(例 `status,screenshot`)

**脅威モデルの境界**: トークンはユーザ専用ファイルに置くため、
同一ユーザ権限で任意コードを実行できるプロセスまでは防げない
(これはあらゆるlocalhostサービスの限界)。信頼境界はローカルユーザアカウント。

ローカルのMCPクライアント(`mcp_stdio.py` 等)はレジストリからトークンを
自動で読むため、利用側の手順は変わらない。
