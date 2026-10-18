# AGENTS.md — AIエージェント向け開発手順

このリポジトリは **Qt WebEngine ベースの QGIS プラグイン**。
プラグインUIは HTML/CSS/JS で実装され、2層の自動検証ができる。

## システム概要

このリポジトリは「プラグイン製品」そのものではなく、
**AIエージェントがQGISを自律駆動してプラグインを開発する環境**である。
システム名は **QGIS Live Harness**(外側の装具=このリポジトリ)。
QGIS内に入る制御プラグインは **QGIS Live Driver**(`qgis_live_driver`)。

```
[エージェント/人間]
   │  MCP (scripts/qgis-mcp.mjs, stdio)  ← .devin/mcp_config.json で登録済
   │  MCP (qgis_live_driver内蔵 /mcp, Streamable HTTP)
   │  MCP (qgis_live_driver/mcp_stdio.py, 同梱stdio shim)
   │  REST (qgis_live_driver内蔵 /api/*) または CLI (npm run live:*)
   ▼
[クライアント層] scripts/live-drive.mjs (LivePage) / qgis-session.mjs
   │  ファイルJSONL: commands.jsonl → results.jsonl
   │  (内蔵HTTP面はワーカースレッドが driver.submit() で同じdispatchへ)
   ▼
[常駐QGISプロセス] WEBENGINE_LIVE_DIR/qgis-<pid>/<plugin_id>/
                    (プラグインごとに独立したlive dir。複数プラグイン同居可)
   ├─ deploy済み <id>(既定 webengine_plugin) = 「器/ドライバ」(ほぼ不変)
   │    LiveDriver: eval(任意JS) / pyeval(任意Python) /
   │                 screenshot / devreload
   └─ 開発対象 = repo側の bridge.py/logic.py/ui/*
        (WEBENGINE_DEV_SRC から別名import。devreloadで即反映)
```

ポイント:
- **QWebEngineViewが実物ChromiumであることがAI自動化の根幹**。
  UI(HTML/CSS/JS)がそのまま通常ブラウザで動くため、Playwright/DevTools等の
  Web標準の自動化資産をそのまま流用できる(L1)。実QGIS内ではCDPが使えない
  環境のためLiveDriverで代替しているが、検査対象が「DOM+JS+WebChannel」の
  Web資産である点は変わらない
- **deployするのは器だけ**。ロジック/UIはリポジトリに置いたまま実QGISで動く
- **pyeval でQGIS内部(iface/QgsProject/canvas)を直接assertできる**
- **編集→`npm run live:devreload`→検証 のループに再起動もdeployも不要**
- MCPサーバを通せばエージェントから `qgis_pyeval` 等のtoolとして使える

## 構成

- `qgis-plugin/` — プラグイン群のルート。**フォルダ名=プラグインID**で複数管理。
  `webengine_plugin/` がその1つ。QGIS依存は `bridge.py` に閉じ込める。
  deploy時に `python/plugins/<フォルダ名>` へ配置される。
  `qgis_live_driver/` はWebEngineを持たない制御専用プラグイン(pyeval+地図キャンバス
  スクショのみ)で、任意プラグインの遠隔操作基盤として常駐させられる。
  内蔵HTTPサーバ(`/mcp`=MCP Streamable HTTP、`/api/*`=REST)と
  同梱stdio shim(`mcp_stdio.py`)も持ち、接続情報は
  `~/.qgis-live/<pid>-qgis_live_driver.json` に書き出す(QGIS_LIVE_REGISTRYで変更可)
- `qgis-plugin/<id>/logic.py` — QGIS非依存の純粋ロジック。pytest対象
- `qgis-plugin/<id>/live_driver.py` — L2検証用。実QGIS内でJS実行を仲介(後述)
- `qgis-plugin/<id>/ui/` — HTML/CSS/JSフロントエンド。QGIS無しの通常ブラウザでも動く(mock使用)
- `qgis-plugin/<id>/ui/src/mock-bridge.js` — Pythonブリッジのモック。**bridgeメソッド追加時は必ず同期更新**
- `plugin.config.json` — 開発対象プラグインのID(qgis-plugin/下のフォルダ名)。
  別プラグイン開発時はここを切り替える
- `tests/e2e/` — Playwrightテスト(L1=mock)
- `tests/unit/` — pytest(logic.py等)

## 検証ループ(変更時はこの順で回す)

```powershell
# L1: UI単体テスト(QGIS不要)。最も頻繁に回す
npm test

# 単体: Pythonロジック
npm run test:unit
```

### L2: 実QGISでの検証

```powershell
# QGIS常駐インスタンスを用意(起動済みならアタッチ、未起動ならdeploy+起動を自動化)
npm run live:ensure
#   → live dirが応答すれば再利用、無ければdeploy-plugin.ps1 -Copy +
#     WEBENGINE_DEV_SRC等のenv付きでQGISを起動してLiveDriver応答までポーリング

# ★普段のコード反映はこれだけ。bridge.py/logic.py/ui/* の変更を即反映。
#   deployもreloadPluginも再起動も不要
npm run live:devreload
#   → repo側の qgis-plugin/<id>/ を別名パッケージ(<id>_devsrc)として再importし、
#     WebChannelのbridgeオブジェクトを差し替えてページを再読み込みする

# プラグインの器側(main_plugin.py, live_driver.py等)を変更した時だけこちら
npm run live:reload     # = deploy -Copy → pyevalで sys.modules掃除+reloadPlugin
#   + open_dialog し直し。--no-deploy でdeploy省略可( junction配置なら不要)

# 実QGIS内UIを検証(QGIS未起動でも内部でensureして自動起動)
npm run test:live       # test-results/qgis-live.png にスクショも残る

# 手動で個別に回したい場合の旧手順も引き続き使える
npm run deploy          # プラグイン配置(junction既定、失敗時copyにフォールバック)
npm run verify:qgis     # 別ターミナルでQGIS起動(開きっぱなし)
```

## L2の仕組み(重要)

**この環境(QGIS 4.0.1 / QtWebEngine 6.8.1 / Chrome 122)では Playwright は使えない。**
CDPポートは開くが `connectOverCDP` は Browser context 非対応で失敗、
ページ直結wsでも `Runtime.evaluate` が一切応答しない(QtのCDP実装の制限)。

代わりに **ファイル経由ライブドライバ** を使う:

- プラグイン側 `live_driver.py` が `WEBENGINE_LIVE_DIR/qgis-<pid>/<plugin_id>/commands.jsonl` を
  QTimerでポーリングし、`view.page().runJavaScript()` でJSを実行、
  結果を `results.jsonl` に返す。`screenshot` コマンドは `view.grab()` でPNG保存
- `pyeval` コマンドは **QGISプロセス内で任意Pythonを同期実行**し結果をJSON化して返す。
  式ならeval、文ならexec(`result`変数への代入が返却値)。名前空間に
  `iface`/`view`/`driver`があり持続する → `iface.activeLayer().name()` 等で
  QGIS内部状態を直接assertできる。任意コード実行なのでWEBENGINE_LIVE_DIR
  設定時のみ有効
- `devreload` コマンドは `WEBENGINE_DEV_SRC` 指定時のみ有効。リポジトリ側の
  `qgis-plugin/<id>/` を `<id>_devsrc` として別名importし直し、
  WebChannelのbridgeを差し替えてview.reload()する。**プラグイン本体(deploy物)は
  「器」で、開発対象のロジックはリポジトリに置いたまま動く**。器側
  (main_plugin.py/live_driver.py/__init__.py)の変更はdevreloadでは反映されず
  `live:reload` が必要
- クライアント側 `scripts/live-drive.mjs` (`LivePage`クラス)が
  `evaluate()` / `pyeval()` / `devreload()` / `waitFor()` / `click()` /
  `screenshot()` / `status()` / `openPlugin()` / `reloadPlugin()` /
  `bridgeCall()` を提供。使い勝手はPlaywright相当。`resolveLiveDirs` が
  live中の全プラグインdirを列挙する
- **ドライバ共通コマンド**(両live_driver.pyに実装。`_handle(cmd, reply)` の
  reply注入で転送にも対応):
  `status`(pid/プラグイン一覧/view有無/http_port) /
  `open_plugin`(load+start+open_dialog) /
  `reload_plugin`(sys.modules掃除+reloadPlugin+open_dialog。
  `live:reload` はこれを優先し、旧ドライバではpyevalにフォールバック) /
  `bridge_call`(bridgeメソッドをプロセス内で直接呼ぶ。WebChannelを通らない
  ためレンダラー飢餓中でも動く。JSON文字列返値はパースされる)
- **`plugin_id` ルーティング(ハブ)**: `eval`/`pyeval`/`screenshot`/`devreload`
  に `plugin_id` を付けるとそのプラグインのLiveDriverへ転送され、結果は
  呼び出し元のresults.jsonlに返る。qgis_live_driver のlive dir 1箇所
  (または内蔵HTTPポート1本)で全プラグインを制御できる。pyeval転送は
  対象プラグインの名前空間(その `view`/`driver`)で実行される。
  `screenshot` は `target` 指定可: driver側 canvas|mainwindow、
  webengine側 view|window|canvas|mainwindow
- **commands.jsonl は append-only。絶対に切り詰めないこと**(LivePage.reset()は
  results.jsonlのみ消す)。ドライバは読み取りoffsetを保持するため、
  切り詰め後にファイルが旧offsetを超えて再成長すると「縮小」と検出できず、
  コマンド行の途中から読み出して JSONDecodeError+コマンド喪失になる。
  同じlive dirに複数クライアントプロセス(テストとMCP等)を同時に
  ぶつけてはいけない — 片方のresetが他方の結果を消す
- 複数QGISインスタンス・複数プラグインが同居しても `qgis-<pid>/<plugin_id>`
  で分離される。deployは `qgis-plugin/` 直下の全プラグインを一括配置し、
  `live:*`/`test:live` は検出した全プラグインに対して実行される
- `scripts/qgis-session.mjs` が `ensure`(起動中へのアタッチ/自動起動)と
  `reload`(deploy+ホットリロード)、`devreload`(repo側再読込)を提供。
  `test:live` も内部でensureするため事前起動は不要になった
- `scripts/qgis-mcp.mjs` は **MCPサーバとして同経路を公開**する(stdio)。
  `.devin/mcp_config.json` で `qgis-live` として登録済み。
  argsはリポジトリ相対パス(`scripts/qgis-mcp.mjs`)で、cwd=プロジェクトルート前提。
  相対パスが解決されない環境では gitignore済みの
  `.devin/mcp_config.local.json` に絶対パスで同名サーバを定義すれば上書きできる。
  VS Code Copilot向けには `.vscode/mcp.json`(`servers` + `${workspaceFolder}`)を同梱。
  tools: `qgis_ensure` / `qgis_pyeval` / `qgis_eval` / `qgis_bridge_call` /
  `qgis_screenshot` / `qgis_status` / `qgis_open_plugin` /
  `qgis_devreload` / `qgis_reload`。
  各toolは内部でensureするためQGIS未起動でも自動で立ち上がる。
  qgis_live_driver がlive中ならhubとして使い、`pluginId`引数は
  plugin_idルーティングに載る。stdoutはプロトコル専用のためログはstderrに出る。
  **プラグイン側にもMCP/REST面がある**: `qgis_live_driver` が `POST /mcp`
  (Streamable HTTP)と `POST /api/*`(REST、汎用 `/api/cmd` 含む)を内蔵し、
  同梱 `mcp_stdio.py` がstdioクライアントをファイルJSONLへ中継する(Node不要)。
  toolsは `qgis_<コマンド種別>` の命名でドライバの全コマンドに対応
  (pyeval/eval/screenshot/devreload/status/open_plugin/reload_plugin/bridge_call)。
  **`QGIS_LIVE_API_KEY`/`QGIS_LIVE_TOOLS` env(QGIS起動時に設定)で
  /mcp・/api/* にAPIキー認証+コマンド種別フィルタが効く**。
  Copilot Studio等のクラウドMCPクライアントから接続する際は
  これらを有効化してトンネル公開する
  (手順: qgis_live_driver/README.md「外部公開」)
- **ドライバは起動時にcommands.jsonlの末尾から読み始める**。reloadでドライバが
  作り直されても過去コマンドの再実行は起きない
- コマンドidはクライアント側でセッションprefix付き(`s<rand>-<n>`)にする。
  reset無しでアタッチしても過去の結果を誤読しない。JS側の結果受け渡しは
  `console.log("__live <cid> <n> <i> <chunk>")` → `_LiveConsolePage.
  javaScriptConsoleMessage`(WebChannel非依存の一方向通知)でpushされる

## 環境固有の制約(ハマりやすい点)

- **`QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu --no-sandbox --disable-gpu-compositing` が必須**。
  未設定だとGLESコンテキスト作成に失敗し、レンダラーが死んで
  `loadFinished=False`・`runJavaScript`が常に`None`を返す(verify-in-qgis.ps1で設定済み)
- **`supportsQt6=yes` が metadata.txt に必須**(無いとQt6ビルドがプラグインを読まない)
- **bridgeの重いQGIS操作は `QTimer.singleShot(0, ...)` で遅延させること**。
  WebChannel経由の呼び出しは同期で、重い処理(レイヤーアクティブ化・再描画等)をすると
  レンダラーのJSスレッドがブロックされ後続のrunJavaScriptまで飢餓する(bridge.py参照)
- **WebChannel sendの飛行中は renderer->browser の他メッセージも全て喪失する**(Qt6.8実測)。
  send返信待ちに割り込んだ `runJavaScript` は返信を殺してチャネルをwedgeさせ、
  `console.log` も同様に届かない。対策として live_driver は
  (a) eval結果を `__live_res` ポーリングしない、(b) eval投入をpending空まで直列化、
  (c) 結果報告を console.log一方向通知+タイムアウトまでの定期再送、にしている。
  `.click()` 等が起こしたsendの返信が重い処理で遅れるとその間のeval結果報告は
  全て落ちるため、GUIブロックが長いプロジェクトではクリック系チェックがWARNになる
- プラグイン有効化は `QGIS4.ini` の `[PythonPlugins]`。deployスクリプトが自動書き込み
- **.ps1はUTF-8 BOM必須**。BOM無しだとWindows PowerShell 5.1がANSI誤読し、
  日本語コメントの直後の文が実行されない(静かに失敗する)
- `qgis-plugin/<id>/ui/` は **ESモジュール不可**。`file://` 直読みのためクラシックスクリプト+グローバル名前空間
- `bridge.py` の新メソッドはJSON文字列を返す(JS側は `BridgeClient.callJson` で受ける)
- `qgis-plugin/<id>/ui/index.html` の `qrc:///qtwebchannel/qwebchannel.js` はQGIS内でのみ解決可能。
  通常ブラウザでは読み込み失敗するが正常動作(mockにフォールバック)
- QGISターゲット: **4.0.1**(`C:\Program Files\QGIS 4.0.1`)、Qt6/PyQt6。
  `qgis.PyQt` shim経由でimport。`runJavaScript`はQt6で`(script, worldId, callback)`シグネチャ

## UI確認のコツ

- L1(Playwright): `page.screenshot()` のPNGはそのまま読んで視覚確認できる
- L2(LivePage): `page.screenshot(path)` で実QGIS内のUIをPNG化→画像として読める。
  `evaluate()` でDOM状態・bridge呼び出し結果を直接確認できる
- `test-results/plugin_load.log` にプラグイン側の診断ログが残る(環境変数・起動経路)
