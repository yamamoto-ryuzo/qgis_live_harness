# QGIS Live Driver (`qgis_live_driver`)

実行中のQGISプロセスを**外部アプリから遠隔操作**するための、
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

**詳細ドキュメント(コマンド一覧・制御範囲・RESTエンドポイント・外部公開手順等):**
https://yamamoto-ryuzo.github.io/qgis_live_harness/driver.html

## 有効化

```powershell
# このリポジトリから(全プラグイン一括deploy)
powershell -ExecutionPolicy Bypass -File scripts/deploy-plugin.ps1 -Copy

# または手動: このフォルダを python/plugins/qgis_live_driver/ へコピーし、
# QGISのプラグイン管理で有効化
```

起動時に `WEBENGINE_LIVE_DIR` が必要(未設定なら何もしない無害なプラグイン):
`scripts/verify-in-qgis.ps1` が付与して起動する。

## セキュリティ

`pyeval` は **任意コード実行**。**開発専用**であり、
エンドユーザーへの配布物に含めてはいけない
(metadata.txtにも `Development-only` と明記済み)。

HTTPサーバは `127.0.0.1` のみにバインドするが、ローカルマシン上の
任意プロセスからQGIS内部を操作できるため、リモート公開は想定しない。
外部公開する場合は必ず `QGIS_LIVE_API_KEY` で認証を有効にし、
`QGIS_LIVE_TOOLS` で `pyeval` を含まない最小限のツールに絞ること
(手順: 上記ドキュメントの「外部公開」)。
