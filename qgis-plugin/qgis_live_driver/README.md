# QGIS Live Driver (`qgis_live_driver`)

実行中のQGISプロセスを**同じPC上のクライアント(AIツール等)から遠隔操作**するための、
UIを持たない制御専用プラグイン。
`python/plugins/` へのコピーだけで任意のQGISインストールに単独導入できる
(リポジトリ・Node不要)。

`webengine_plugin` と違い `QWebEngineView` を持たないため、
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
