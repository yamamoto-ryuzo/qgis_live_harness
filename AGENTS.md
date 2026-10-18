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
   ├─ deploy済み <id>(plugin.config.json の id) = 「器/ドライバ」(ほぼ不変)
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
  **各プラグインは「1つのQGISプラグイン配布物」として自律管理する**:
  `metadata.txt`(バージョンの正)・`LICENSE`・`README.md`(+`README_JP.md`等
  の言語別・`SEARCH.md`/`SPEC.md`等の詳細文書)・`CHANGELOG.md`
  (そのプラグインの変更履歴)をフォルダ内に持つ。
  upstreamリポジトリがあるプラグイン(geo_search=GEO-search-plugin、
  geo_webview=geo_webview、geo_report、geo_import、
  QGIS-legendView-main=QGIS-legendView)の文書はupstream版を復元・追従し、
  Harness側での追加・変更はそのプラグインのCHANGELOGに
  新バージョンエントリとして記録する(metadata.txtのversionも同期して上げる)。
  **プラグイン固有の変更をルートのCHANGELOG.mdではなく
  プラグインのCHANGELOG.mdに書くのが原則**(ルートCHANGELOGは
  Harness基盤・横断的変更用)。upstreamに公開する場合はそちらにも反映する。
  現在は `qgis_live_driver/` と検証対象 `geo_search/` `geo_webview/`
  `geo_report/` `geo_import/` `QGIS-legendView-main/`、および
  Harness生まれの `geo_excel/`(下記)を管理する。
  実体はすべてこのrepo内のgit管理対象(Harness側が正本)。
  upstreamリポジトリとの同期基盤は構造で2形式に分かれ、
  `npm run upstream -- <repo> <git引数>`(scripts/upstream-git.ps1。
  例: `npm run upstream -- geo_report status`)が形式を吸収する:
  - repo内にプラグインsubfolderを持つupstream(geo_report、geo_import)は
    upstreamとの同期が必要な場合に `C:\devin\<repo>` または
    `.upstream/<repo>/` にcloneし、subfolderを `qgis-plugin/<id>` への
    junctionに置き換える(例: `<clone>/geo_report` → `qgis-plugin/geo_report`)。
    cloneが無い間はHarness側が唯一の正本
  - 「repoルート=プラグイン/コンテンツ」構造のupstream
    (QGIS-legendView→QGIS-legendView-main、QGIS-exportExcel→geo_excel)は
    subfolder junctionが張れないため、**upstream側の `.git` を
    `.upstream/<repo>.git` に退避し `core.worktree` を `qgis-plugin/<id>` に
    向けたgitdir運用**。直接叩く場合は
    `git --git-dir=.upstream/<repo>.git <args>`(core.worktree設定済み)
  (旧サンプル `webengine_plugin` は削除済み。
  WebEngineプラグインの構成例はgit履歴を参照)。WebEngineプラグインでは
  QGIS依存は `bridge.py` に閉じ込める。deploy時に `python/plugins/<フォルダ名>` へ配置される。
  `geo_excel/` は upstream `QGIS-exportExcel` のレイヤアクション用
  スクリプト群(プラグインではない)を簡易プラグイン化したもので、
  スクリプト本体は無改変で同梱し `plugin.py` が実行時に
  `[% @layer_id %]`/`[% $id %]` をアクティブレイヤ/選択地物で置換して
  exec する(QGIS4/Qt6では `import PyQt5` がブロックされるため
  exec直前に `PyQt5`→`qgis.PyQt` へソース書き換え。実行には
  win32com+Excelが必要)。upstream側は
  `.upstream/QGIS-exportExcel.git` のgitdir運用。
  `geo_excel` は `bridge.py`(`GeoExcelBridge`)を `plugin.bridge` に配線済みで、
  geo_searchと同じく `bridge_call`/`describe_plugins` から利用できる。
  メソッド: `pluginInfo`/`status`/`listScripts`/`layerVariables`/
  `setLayerVariables`(xlsout_*・dpi変数の取得設定)/
  `run(script, feature_id, confirm)`(帳票実行。modal QMessageBoxは
  実行中だけ自動応答に差し替え、confirm=False既定では確認系をCancel=
  中断として扱う。Excel生成中はGUIスレッドをブロック)
  `qgis_live_driver/` はWebEngineを持たない制御専用プラグイン(pyeval+地図キャンバス
  スクショのみ)で、任意プラグインの遠隔操作基盤として常駐させられる。
  内蔵HTTPサーバ(`/mcp`=MCP Streamable HTTP、`/api/*`=REST)と
  同梱stdio shim(`mcp_stdio.py`)も持ち、接続情報は
  `~/.qgis-live/<pid>-qgis_live_driver.json` に書き出す(QGIS_LIVE_REGISTRYで変更可)。
  さらに **AIアシスタントパネル**(`ai_panel.py`+`ai_client.py`)を内蔵:
  `プラグイン > QGIS Live Driver > AI アシスタント` で開くQtドックで、
  OpenAI互換(`/chat/completions`)・Gemini(`generateContent`)・
  GitHub Copilot(GitHubトークンを `copilot_internal/v2/token` で
  短期トークンに交換し、応答の `endpoints.api` へ。
  Pro/Business/Enterprise/EMU対応・失敗時は `copilot_internal/user`
  でAPI先解決+生トークンBearerにフォールバック。
  パネルの「GitHubでサインイン」はOAuthデバイスフロー)の
  APIを接続すると、モデルが `mcp_http.TOOLS` のツール群を
  `driver.submit()` 経由でループ実行する。リモート制御OFF時は
  パネル専用の内部ドライバで動く
- `qgis-plugin/<id>/logic.py` — QGIS非依存の純粋ロジック。pytest対象(WebEngineプラグインの構成)
- `qgis-plugin/<id>/live_driver.py` — L2検証用。実QGIS内でJS実行を仲介(後述)
- `qgis-plugin/<id>/ui/` — HTML/CSS/JSフロントエンド。QGIS無しの通常ブラウザでも動く(mock使用)
- `qgis-plugin/<id>/ui/src/mock-bridge.js` — Pythonブリッジのモック。**bridgeメソッド追加時は必ず同期更新**
- `qgis-plugin/<id>/bridge.py` — AI/外部制御用ブリッジ(**このrepoで管理する
  プラグインはAI制御フル対応を前提とする**)。`<id>Bridge` クラスを定義し
  `plugin.bridge` に配線すると、`qgis_live_driver` の `bridge_call`
  (ファイルJSONL / REST /api/cmd / MCP `qgis_bridge_call` /
  AIアシスタントパネル)と `describe_plugins` カタログから利用できる。
  フル対応の要件:
  - `pluginInfo()` を標準スキーマ(id/name/summary/when_to_use/invoke/
    methods/state)で実装し、AIが用途と呼び方を自己発見できるようにする
  - プラグインの主要機能をJSON文字列を返すメソッドとして公開する
    (ドメインエラーは `{"ok": false, "error": ...}`、予期しない例外は
    driver側の {"error": traceback} に委ねる)
  - modalなQMessageBox等が呼出をブロックしないよう自動応答等で吸収する
    (geo_excelの _DialogAutoReply 参照)
  - GUIスレッドを長時間占有する処理はその旨をdocstringに明記する
  実装例は `geo_search/bridge.py`(高機能)と `geo_excel/bridge.py`(小規模)。
  **全管理プラグインが配線済み**: `qgis_live_driver`・`geo_search`・
  `geo_webview`・`geo_excel`・`geo_report`・`geo_import`・
  `QGIS-legendView-main`
  (新規プラグイン追加時もbridge.py同梱が前提)
  なお **bridgeを持たないプラグインにもドライバ側の汎用アダプタ
  `live_driver._GenericBridge` が自動フォールバックする**
  (`pluginInfo`/`status`/`actions`/`trigger`/`run`/`openDialog`/
  `closeDialog`。`run`/`trigger`はQTimer.singleShotで非同期発火のため
  modalダイアログを開いても応答をブロックしない)。
  `describe_plugins` では `generic: true` としてmetadata由来の
  自己記述が載るため、mmqgis等のサードパーティ製プラグインも
  repo外改変なしでAIが発見・操作できる
- `plugin.config.json` — 開発・検証対象プラグインのID(qgis-plugin/下のフォルダ名)。
  **文字列または配列**: 先頭=主開発対象(MCPツール等のデフォルトpluginId)、
  全要素=live:reload/test:liveの対象。現在は
  `["geo_search","geo_webview","geo_report","geo_import","geo_excel","QGIS-legendView-main","qgis_live_driver"]`。
  live dirを持たない対象(geo_search等)はtest:liveでhubドライバ経由の
  open_plugin/pyeval/run()/スクショが検証される
- `tests/e2e/` — Playwrightテスト(L1=mock)。**現在specなし**
  (webengine_plugin削除と共に除去。serve-ui.mjs/playwright.config.ts等の
  L1基盤は残置。WebEngineプラグイン追加時にspecを作る)
- `tests/unit/` — pytest(mcp_http/ai_client/credential_store等のstdlib層)

## ハイブリッド構造(固定方針)

**制御面は「プラグイン内の薄いプリミティブ + 外側のオーケストレーション」の
2層を固定とする。今後もこの構造で開発する。**

```
[プラグイン内] 即応答の実行プリミティブ
   pyeval / status / open_plugin / reload_plugin / screenshot / bridge_call /
   describe_plugins
   ※各コマンドはGUIスレッドで即時実行し、例外は {error: ...} として返す
        │  REST(/api/*) / MCP(/mcp) / ファイルJSONL
[外側] オーケストレーション
   順序制御・待機・リトライ・タイムアウト・結果集約・レポート
   (live-drive.mjs / qgis-session.mjs / qgis-live-check.mjs / pytest)
```

理由(実測済み):

- **GUIスレッドを占有しない**: dispatchはGUIスレッドで動くため、
  待機・sleep・多段処理をインプロセスに入れるとQGIS UIをブロックし、
  ドライバ自身が無応答になる(pyeval内のdriver.submit自己デッドロック、
  重いfindChildrenクエリの無応答を実測)
- **クラッシュ分離**: 検証・クライアント側の障害でQGISを巻き込まない
- **タイムアウト/リトライは外側でしか制御できない**: ホスト側が
  処理中のコマンドを打ち切る手段は、クライアント側の放棄しかない

### エラー処理の契約(境界の両側で必須)

- **プリミティブ側(プラグイン内)**: コマンドの失敗は必ず
  `{"error": "<msg>"}` を返し、例外を外へ漏らさない
  (呼び出し元は `reply["error"]` の有無で判定できる)
- **境界**: HTTPエラー・接続失敗・応答形式不正はクライアント側で
  `ApiError`等の例外に変換し、タイムアウトは常にクライアント側で管理
- **オーケストレーション側**: 個別チェックの失敗は集約して続行
  (test:liveのcheck()/WARN継続パターン)。「検証自体が死ぬ」
  ケースだけ即FAILにして次プラグインへ進む
- **新しいコマンドを追加する時**: 上記3点(即応答・error返却・
  GUIブロック禁止)を満たすこと。長時間処理が必要なら
  状態付きコマンド(start→poll→result)に分割し、待機は外側に置く

## 検証ループ(変更時はこの順で回す)

```powershell
# 単体: Pythonロジック・stdlib層(mcp_http/ai_client/credential_store)
npm run test:unit

# L1(UI単体のPlaywright)は現在specなし。
# WebEngineプラグイン追加時に tests/e2e/ へspecを置き npx playwright test
```

### L2: 実QGISでの検証

**標準の検証対象プラグインは `geo_search`・`geo_webview`・`geo_report`・
`geo_import`・`geo_excel`・`QGIS-legendView-main`**(実体は
`qgis-plugin/<id>` = このrepoのgit管理対象。
deploy先 `geo_custom/python/plugins/<id>` はここへのjunction。
upstream同期は `.upstream/` 経由(前述。いずれもHarness側が正本)。Qt Widgetsプラグインでrepo側編集→`reload_plugin`で即反映できる。
`open_plugin`/`reload_plugin`/
`status`/`screenshot(mainwindow)` の対象になり、pyevalからは
`qgis.utils.plugins['<id>']` で `dialog`/`run` 等に直接触れられる。
AIパネルの実用検証にも使う(例:「geo_searchの検索ダイアログを開いて」)。
なお `view` を持たないため `eval`/`devreload` の
WebEngine固有検証の対象にはならず、`plugin_id`転送先にもなれない
(転送対象にするには対象プラグイン側にlive_driver.py同梱が必要)。

**geo_search のAI向けAPI(`bridge_call`)**: `geo_search/bridge.py` の
`GeoSearchBridge` が `plugin.bridge` に配線されており、hubドライバの
`bridge_call` が `plugins['geo_search'].bridge.<method>(*args)` を直接呼ぶ
(WebChannelを通らないローカルコマンドなのでview不要。ファイルJSONL/
REST/MCP `qgis_bridge_call` 全経路で利用可)。
メソッドはJSON文字列を返す:

- `pluginInfo()` — プラグインの自己記述(下記「AI向けプラグインカタログ」の
  標準スキーマ: id/name/summary/when_to_use/invoke/methods/state)
- `status()` — 実行時状態(現在タブ/入力値/結果概要)
- `listTabs()` — 検索タブ一覧(フラットindex/group/title/layer/fields)
- `selectTab(tab)` — tab: int(フラットindex)/タイトルstr/{group,title}
- `search(query, tab=None, show=True, zoom=True, max_features=200)`
  — 検索ボタン押下と同じ `show_features` 経路で実行し、
  `result_dialog._tabs` を構造化して返す(レイヤ別count/属性/centroid)。
  query は str(先頭入力欄)/list(各入力欄)/dict({Field名 or ViewName
  or 表示ラベル: 値})
- `results(max_features)` — 直近結果の再取得(再検索しない)
- `zoom(feature_ids=None, tab_index=0)` — 結果地物へズーム
- `openDialog()` / `closeDialog()`
- `searchOptions(options)` — 検索オプション get/set:
  `pan_mode`(0選択フィット/1中心パン/4固定縮尺/5アニメーションパン/
  6選択のみ)・`fixed_scale`・`show_layer_name`。全タブへ適用し
  ダイアログのコンボ/チェックも同期。`search` の `options` 引数でも同値を受ける
- `tabOptions(tab, options)` — タブ固有コントロール get/set。
  地番検索: `match`=exact|fuzzy・`aza_code`(字コードテーブル選択)。
  所有者検索: `fields`=[対象ViewName]・`match_mode`=partial|forward
- `suggest(tab, field, limit)` — 検索フィールドのユニーク値一覧
- `listThemes()` / `applyTheme(name, additive=None)` /
  `themeAdditive(enabled)` — マップテーマ一覧・適用・追加表示(union)
- `saveUserTheme(path=None)` / `loadUserTheme(path)` —
  ユーザーテーマ(.usertheme.json)の保存/読込適用
- `getSettings()` / `setSettings({geo_search_json}, rebuild)` —
  設定由来と geo_search_json パスの取得/設定
- `tabSetting(tab)` / `addTabFromCurrentLayer(title)` /
  `removeTab(tab)` / `reloadDialog()` — タブ設定JSON参照・
  現在レイヤのタブ追加(プロジェクト変数)・タブ削除
  (由来=_sourceに応じ setting.json/geo_search_json/プロジェクト変数から除去)
  ・ダイアログ再構築。add/removeは確認ダイアログ無しで直接実行される点に注意

例(MCP): `qgis_bridge_call pluginId="geo_search" method="search" args=["○○町"]`
pyevalからも `plugins['geo_search'].bridge.search("○○町")` で直接呼べる。
コード変更の反映は junction 配置なら `reload_plugin`、
copy配置なら `npm run deploy` + `reload_plugin`。

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

## リリース

- **リリースタグ(`git tag`)・GitHub Release はユーザーの明示的な指示がない限り作成しない**
- バージョンは `package.json` がリポジトリ(Harness)のバージョン、
  各 `qgis-plugin/<id>/metadata.txt` がプラグイン個別のバージョン(別系で管理)
- 変更履歴は `CHANGELOG.md` (Harness基盤) と
  `qgis-plugin/<id>/CHANGELOG.md` (プラグイン個別) に記録する。
  プラグイン個別の変更を反映する時は **そのプラグインの
  CHANGELOG.mdにエントリを追加し metadata.txt の version も上げる**
  (新機能=マイナー、修正=パッチを目安。geo_search/geo_webviewは
  upstreamリポジトリの履歴形式に従う)

## L2の仕組み(重要)

**この環境(QGIS 4.0.1 / QtWebEngine 6.8.1 / Chrome 122)では Playwright は使えない。**
CDPポートは開くが `connectOverCDP` は Browser context 非対応で失敗、
ページ直結wsでも `Runtime.evaluate` が一切応答しない(QtのCDP実装の制限)。

代わりに **ファイル経由ライブドライバ** を使う:

- プラグイン側 `live_driver.py` が `WEBENGINE_LIVE_DIR/qgis-<pid>/<plugin_id>/commands.jsonl` を
  QTimerでポーリングし、`view.page().runJavaScript()` でJSを実行、
  結果を `results.jsonl` に返す。`screenshot` コマンドは `view.grab()` でPNG保存。
  **ファイル経由コマンドは `token` フィールド必須**(値は `<live_dir>/token`
  にドライバが書き出す。LivePage/mcp_stdio.py は自動で読んで付与する)
- `pyeval` コマンドは **QGISプロセス内で任意Pythonを同期実行**し結果をJSON化して返す。
  式ならeval、文ならexec(`result`変数への代入が返却値)。名前空間に
  `iface`/`view`/`driver`があり持続する → `iface.activeLayer().name()` 等で
  QGIS内部状態を直接assertできる。任意コード実行のため全チャネルで
  セッショントークン認証を必須化(下記「セキュリティ」)
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
  ためレンダラー飢餓中でも動く。JSON文字列返値はパースされる) /
  `describe_plugins`(ロード済み全プラグインのカタログ。bridgeを持つものは
  各pluginInfo()の自己記述を集約。下記「AI向けプラグインカタログ」)
- **AI向けプラグインカタログ**: 「どのプラグインをいつどう使うか」の
  発見経路。bridgeを持つプラグインは `pluginInfo()` が標準スキーマ
  `{id, name, summary, when_to_use[], invoke, methods[{name, signature,
  description, example}], state}` を返す契約(methodsはsignature/
  docstring自動生成+bridge.py内の補足定数)。`describe_plugins` コマンドが
  全プラグイン分を集約して返し、REST `/api/cmd`・`/api/tools`・
  MCP `qgis_describe_plugins`(qgis-mcp.mjs/mcp_http.py/mcp_stdio.py
  いずれも)で公開される。AIは `describe_plugins` で選択→
  `bridge_call` で実行の2段で使う。bridge付きプラグイン追加時は
  pluginInfo() をこのスキーマで実装すること
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
  `qgis_describe_plugins` / `qgis_screenshot` / `qgis_status` /
  `qgis_open_plugin` / `qgis_devreload` / `qgis_reload`。
  各toolは内部でensureするためQGIS未起動でも自動で立ち上がる。
  qgis_live_driver がlive中ならhubとして使い、`pluginId`引数は
  plugin_idルーティングに載る。stdoutはプロトコル専用のためログはstderrに出る。
  **MCPサーバプロセスは起動時のコードを保持する**ため、
  scripts/*.mjs 変更後はクライアント側でサーバ再起動が必要
  (旧コードが死んだlive dirを拾ってコマンド喪失→タイムアウトになる事例あり)
  **プラグイン側にもMCP/REST面がある**: `qgis_live_driver` が `POST /mcp`
  (Streamable HTTP)と `POST /api/*`(REST、汎用 `/api/cmd` 含む)を内蔵し、
  同梱 `mcp_stdio.py` がstdioクライアントをファイルJSONLへ中継する(Node不要)。
  toolsは `qgis_<コマンド種別>` の命名でドライバの全コマンドに対応
  (pyeval/eval/screenshot/devreload/status/open_plugin/reload_plugin/
  bridge_call/describe_plugins)。
  **全チャネルでセッショントークン認証が必須**(下記「セキュリティ」)。
  `QGIS_LIVE_API_KEY`/`QGIS_LIVE_TOOLS` env(QGIS起動時に設定)で
  追加キー・コマンド種別フィルタが効く
- **セキュリティ(localhost限定運用)**: ドライバ起動時に
  `secrets.token_hex` でセッショントークンを生成し、
  `<live_dir>/token` とレジストリJSONにユーザ限定ACLで書き出す。
  commands.jsonl の全コマンドは `token` 一致必須、HTTP(/mcp・/api/*)は
  Bearer等の照合必須 + Host/Origin がloopback以外なら拒否
  (DNSリバインド・ブラウザ経由対策)。配布版は
  `プラグイン > QGIS Live Driver > リモート制御 (localhostのみ)`
  トグル(QSettings永続化・初回警告)でも有効化できる。
  env `WEBENGINE_LIVE_DIR` は従来通り優先の開発経路
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
