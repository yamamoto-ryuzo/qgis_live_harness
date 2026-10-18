# QGIS Live Driver (`qgis_live_driver`)

実行中のQGISプロセスを**外部アプリから遠隔操作**するための、
UIを持たない制御専用プラグイン。
QGIS Live Harness(親リポジトリ)の「QGIS側の手」だが、
**Harnessとは独立した汎用部品**であり、
`python/plugins/` へのコピーだけで任意のQGISインストールに単独導入できる
(リポジトリ・Node不要)。

`webengine_plugin` と違い `QWebEngineView` を持たないため、
**WebEngineを使わない任意のQGIS環境・任意の他プラグイン**に対しても
`pyeval` 経由の遠隔操作面を提供できる。

## できること

| コマンド | 動作 |
|---|---|
| `pyeval` | QGISプロセス内で任意Pythonを同期実行し結果を返す。名前空間に `iface` / `QgsProject` / `QgsApplication` / `driver` を持つ → `iface.activeLayer().name()` や `QgsProject.instance().mapLayers()` 等で内部状態を直接取得・操作できる |
| `screenshot` | `iface.mapCanvas().saveAsImage(path)` で地図キャンバスをPNG保存。`target:"mainwindow"` でQGISメインウィンドウを `grab()` |
| `status` | pid / http_port / live_dir / ロード中プラグインと各driver・view有無を返す(生存確認・一覧用) |
| `open_plugin` | `plugin_id` のプラグインをload+startし、`open_dialog` があれば開く |
| `reload_plugin` | `plugin_id` のプラグインを `sys.modules` 掃除+`reloadPlugin`+`open_dialog` でホットリロード(QGIS再起動不要。自プラグイン自身も可) |
| `bridge_call` | `plugin_id` + `method` + `args` で対象プラグインのbridgeオブジェクトを**プロセス内で直接呼ぶ**。WebChannelを通らないためJSレンダラー飢餓中でも動作する。JSON文字列の返値はパースして返す |
| `eval` / `devreload` | viewを持たないため **unsupported エラーを返す**(ハングしない)。ただし `plugin_id` を付けると対象プラグインへ転送される(下記) |

### plugin_idルーティング(ハブ機能)

`eval` / `pyeval` / `screenshot` / `devreload` に `plugin_id` を付けると、
そのプラグインのLiveDriver(`plugin.driver`/`plugin._live`)へコマンドが
転送され、結果は呼び出し元の `results.jsonl` に返る。
つまり**このドライバのlive dir / HTTPポート1本で全プラグインを制御できる**。

- 転送先ドライバは `_handle(cmd, reply)` の `reply` 引数に対応している必要がある
  (repo同梱の webengine_plugin 版 live_driver.py は対応済み)
- `pyeval` を転送すると対象プラグインの名前空間(その `view`/`driver`)で実行される

## 制御可能な範囲

`pyeval` はQGISプロセス内での任意Python実行のため、
**PyQGISで書ける操作は全て制御可能**:

| 対象 | pyevalの例 |
|---|---|
| レイヤー/プロジェクト | `iface.addVectorLayer(...)` / `QgsProject.instance().write()` |
| キャンバス | `iface.mapCanvas().setExtent(...)` / `.refresh()` |
| メニュー/ツールバー | `iface.actionZoomIn().trigger()`、`mainWindow().findChildren(QAction)` で全アクション列挙・実行 |
| 他プラグイン | `qgis.utils.plugins["<id>"]` で他プラグインのオブジェクトに到達 |
| Processing | `processing.run("native:buffer", {...})` |
| 設定 | `QgsSettings().setValue(...)` |
| 任意ウィジェットの画像化 | `widget.grab().save(path)`(pyeval経由) |

**制約:**

- **同期GUIスレッド実行** — pyeval実行中はGUIがブロックし、逆に
  再描画等でGUIビジーの間はポーリングが飢餓する(一時的)
- **OSネイティブダイアログ** — Qt外のダイアログはwidget introspection経由の
  間接操作。Qtモーダルは `QApplication.activeModalWidget()` で `accept()`/`reject()` 可能
- **実マウス/実キー** — `QMouseEvent`/`QTest.mouseClick` のpostで模倣可能だが
  座標変換等の下ごしらえが必要
- **Python API未露出の内部機能** — 稀だがC++ privateな振る舞いは不可

## 接続面(4系統・全て同じdispatchへ)

```
① ファイルJSONL  外部アプリ → commands.jsonl 追記 → QTimer(200ms)実行 → results.jsonl
② HTTP REST     POST 127.0.0.1:<port>/api/pyeval {"code":"..."} → JSON応答
③ MCP HTTP      POST 127.0.0.1:<port>/mcp  (Streamable HTTP, JSON-RPC)
④ MCP stdio     python mcp_stdio.py をspawn → stdio↔①を中継
```

- ②③はプラグイン内蔵の `http.server`(stdlibのみ)が `127.0.0.1` の
  空きポートで提供。ワーカースレッド→ `driver.submit()` メモリキュー →
  GUIスレッドのQTimerが①と同じ経路で実行する
- ポート等の接続情報は **`~/.qgis-live/<pid>-qgis_live_driver.json`** に書き出される
  (`QGIS_LIVE_REGISTRY` で変更可)。クライアントはここから自動検出できる
- ④ `mcp_stdio.py` はstdlibのみで動く同梱shim。spawn側にQGIS/Node不要。
  レジストリからlive dirを自動検出してstdio↔JSONLを中継する

### HTTP RESTエンドポイント

| エンドポイント | 内容 |
|---|---|
| `GET /api/health` | `{"ok":true,"pid":...,"plugin":"qgis_live_driver"}` |
| `GET /api/tools` | ツール仕様JSON(function calling系AIが読む用) |
| `GET /api/status` | `status` コマンドの結果 |
| `POST /api/cmd` | コマンドJSONをそのままdispatch(`{"type":"reload_plugin","plugin_id":"..."}` 等すべて有効) |
| `POST /api/pyeval` | `{"code":"...", "plugin_id":"..."}` → `{"result":...}` |
| `POST /api/eval` | `{"expression":"...", "plugin_id":"<id>"}` → 対象プラグインへ転送(plugin_id無しなら unsupported) |
| `POST /api/screenshot` | `{"path":"...","plugin_id":"...","target":"..."}` → PNGバイナリ(Content-Type: image/png) |
| `POST /mcp` | MCP JSON-RPC (initialize/tools/list/tools/call/ping) |

MCP tools は `qgis_<コマンド種別>` の命名で、引数はコマンドJSONの
キーにそのまま対応する(`plugin_id` / `target` / `method` / `args` 等)。

### 外部公開(M365 Copilot Studio等からの接続)

`/mcp` は Copilot Studio が対応する **Streamable HTTP transport 互換**だが、
既定では `127.0.0.1`・認証なしのためクラウドからは到達しない。

公開手順(APIキー認証 `QGIS_LIVE_API_KEY` / 公開ツール絞り込み
`QGIS_LIVE_TOOLS` / devtunnel・ngrokによるHTTPS化 / Copilot Studio側の設定)は
**[ドキュメントサイト「外部公開」](https://yamamoto-ryuzo.github.io/qgis_live_harness/driver.html#publish)** を参照。

## 仕組み(ファイルプロトコル詳細)

環境変数 `WEBENGINE_LIVE_DIR` が設定された状態でQGISが起動すると、
`initGui` 時に `live_driver.py` が起動し
`WEBENGINE_LIVE_DIR/qgis-<pid>/qgis_live_driver/` をポーリングする:

```
外部アプリ → commands.jsonl に1行1JSONを追記
           → QTimer(200ms)が読み取り実行
           → results.jsonl に {id, result|error} を追記で返却
```

- 輸送層はファイルのみ。**言語非依存**(JSON Linesを追記・読取できれば何でもよい)
- `commands.jsonl` は **append-only**。切り詰めるとドライバのoffsetが
  ずれてmid-line読み(JSONDecodeError+コマンド喪失)を起こす
- 同一live dirへの同時アクセスは **単一クライアント** 前提

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
(手順: 上記「外部公開」のリンク先)。
