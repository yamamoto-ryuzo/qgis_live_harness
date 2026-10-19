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
  `settings`(既定値・環境チェック・要件列挙)/`applyDefaults`/
  `checkExcel`/`openSettings`/
  `run(script, feature_id, confirm)`(帳票実行。modal QMessageBoxは
  実行中だけ自動応答に差し替え、confirm=False既定では確認系をCancel=
  中断として扱う。Excel生成中はGUIスレッドをブロック)。
  さらに `settings.py`+`settings_dialog.py` による既定値自動適用と
  設定UIを持つ(出力先既定=<ドキュメント>/geo_excel、
  テンプレート未指定時はレイヤのフィールドから最小xlsxを自動生成)
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
  パネル専用の内部ドライバで動く。
  指示書は2系統のMarkdown: `~/.qgis-live/agents/*.md` は
  常時注入(パネルで選択・複数対応)、`~/.qgis-live/skills/*.md` は
  一覧のみプロンプトに載せモデルがpyevalのopen()で読む
  オンデマンド手順書。同梱デフォルトは `<plugin>/<kind>/` に置き
  ユーザ側同名ファイルが優先される。指示書自体も
  `ai_*`(list/read/save/delete_instruction + ai_select_agent)
  ツールでモデルが編集・選択できる(パネルローカル実行・保存は
  ユーザ側のみ)。外部オーケストレーター向けには
  `qgis_instruction`ツール(op=list|read|save|delete)を
  MCP/RESTで公開している。逆方向としてAIパネル自体が
  MCPクライアントも持ち、`~/.qgis-live/mcp_servers.json`
  (Claude Desktop互換、command=stdio/url=Streamable HTTP)の
  外部MCPサーバのツールを `mcp_<サーバ>__<ツール>` で使える。
  さらに **ホットリロード**(`hot_reload.py`):
  `プラグイン > QGIS Live Driver > ホットリロード` サブメニューに
  開発対象(deploy先の各プラグインのrealpathが <repo>/qgis-plugin/
  配下に解決されるもの=junction配置のみ。該当なしなら候補なし)を一覧し、
  選んだプラグインを手動で sys.modules掃除+reloadPlugin
  (+open_dialog再表示)する。「すべて再読込」も可
  (qgis_live_driverは最後)。QGIS再起動・deploy不要で、
  Node側 `npm run live:watch`(自動watch)の手動版に相当する。
  さらに **GeoSuite共有ツールバー**(`geo_toolbar.py`):
  管理対象プラグインのツールバー項目を1本の
  `QToolBar`(objectName="GeoSuite")に集約する。
  各プラグインは find-or-create で共有し(ドライバ非依存の
  同形小ヘルパを各プラグインが持つ)、ドライバ有効中は
  **常時表示が強制**される(toggleViewAction無効化+5秒毎に
  再表示)。先頭にドライバが**モードバッジ**
  (開発=「開発モード」の赤背景白文字、利用=歯車アイコンのみで
  非侵襲表示。5秒毎に deploy_state で自動更新、クリックで
  Deploy Modeダイアログ起動)を載せる。geo_search/geo_webview/geo_report/
  geo_import/QGIS-legendView-main のツールバー項目は全て
  GeoSuiteに集約済み。新規プラグインのツールバー項目も
  `addToolBarIcon` ではなくGeoSuiteへ載せること。
  さらに **レイヤ整理サービス**(`layer_org.py`):
  プラグイン横断で追加レイヤの表示を標準化する共有プリミティブ。
  `plugins['qgis_live_driver'].layer_org.place_all([(layer, ctx)])`
  でプロファイルJSONのルールに従いグループ配置・リネーム・
  .qmlスタイル適用する。プロファイルは同梱 `<plugin>/layer_org/*.json`
  + ユーザ `~/.qgis-live/layer_org/*.json`(同名優先)の2階層で、
  アクティブは QSettings `qgis_live_driver/layer_org/profile`
  (bridge `setLayerOrgProfile` で切替)。ルールは match キー
  (format/ext/provider/layer_type/geom/plugin/name_re/dataset_re/
  url_re/tags)の全キーAND先勝ちで、groupパス(`/区切り`)/rename
  テンプレ/style/top/collapsedを適用。bridgeメソッド
  `layerOrgProfiles`/`layerOrgRules`/`setLayerOrgProfile`/
  `organizeLayers`(dry対応)/`placeLayer` 経由でAIからも操作可。
  geo_import は load_resource_clicked で追加したレイヤを自動で
  このサービスに渡し、ドライバ未ロード・無効時は従来のflat追加に
  フォールバックする。他プラグインも同様に place_all を呼べば
  同じ標準化を共有できる
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
実体dir配置(利用モード)は配置内容が固定のため `reload_plugin` のみ
(利用版そのものの更新は `npm run deploy:install`)。

## deployの2モード(開発/利用の明示切替)

このリポジトリは「開発」と「利用(通常使用)」の2側面を持ち、
同じプロファイル内で **deployモードを明示切替する**。

```powershell
npm run deploy         # 開発モードへ切替(junction配置・repo優先)
npm run deploy:use     # 利用モードへ切替(退避版の復元。deploy:copy は旧名エイリアス)
npm run deploy:install # repo現状を利用版として配置(リリース操作)
npm run deploy:status  # 現在モードの確認(宣言+配置物の実態を表示)
```

QGIS側からも切替可能: `プラグイン > QGIS Live Driver > Deploy Mode`
ダイアログ(mode_switch.py)が宣言モードと各プラグインの実配置形態を
表示し、ボタンで `deploy-plugin.ps1` を起動して切替
(任意で非ドライバプラグインを即リロード)。GeoSuiteツールバー先頭の
モードバッジからも同ダイアログを開け、現在モードはバッジに
常時表示される。markerの `repo` キーで
実体dir配置中でもスクリプトを解決する。bridge `deployMode()` で
AIから状態を読取可(切替はUI操作のみ)。

モード宣言は deploy時に `profiles/<profile>/qgis_live_mode.json`
(`{"mode":"dev"|"use"}`)へ書き出される。harness側はこれを読み、
マーカーが無い場合は配置物のjunction実態から推定する。

#### 【最強ルール】deployは全てUI操作。AI/自動経路は配置を変更しない

**`deploy-plugin.ps1`(=プラグインフォルダへのあらゆる書込み)は
AIエージェント・自動スクリプトから一切呼ばない。**
`qgis-session.mjs` はdeploy経路をコードとして持たない
(`live:ensure`/`live:reload`/`test:live` はQGIS起動/接続のみ行う)。
つまり:

- dev→use・use→dev・install 全てのモード遷移はUI操作のみ
- 開発モードでなければrepo編集の反映経路自体が存在しない
  (junctionも `WEBENGINE_DEV_SRC` も無い)。非devモードでは
  AIの操作はMCP系(pyeval/bridge_call/status/screenshot等)のみで、
  プラグインの内容を変える手段は何もない
- AIが書き換えてよいのは **repo内の作業ツリーだけ**。
  `python/plugins/`・`qgis_live_parked/` への書込み経路を
  新たに作らないこと

#### 例外: ユーザーの明示承認に基づく代理実行は可

**ユーザーが開発モードでない状態(未配置/利用モード/不明)で
開発作業(コード編集・修正依頼・テスト実施等)を開始しようとしたら、
AIは作業に入る前に「開発モードに切り替えますか?」と尋ねること。**
ユーザーが「はい」と答えた場合のみ、AIが `npm run deploy` を
実行してよい(ユーザー指示の代行であり自動切替ではない)。
同様に開発終了時の `deploy:use` やリリース時の `deploy:install` も、
ユーザーの明示指示があればAIが実行してよい。
確認なしの無断切替・自動切替は禁止のままとする。

- **開発モード(dev) = junction 配置(repo優先・既定)**:
  `npm run deploy`(UI操作)のみが張る。
  切替時に `python/plugins/<id>` に既存の実体dir(利用版)があれば
  **`profiles/<profile>/qgis_live_parked/<id>` へ退避**してから
  junctionを張る(python/plugins外のためQGISには完全に見えない。
  `_user`リネーム等でplugins内に残すと別IDプラグインとして
  認識されてしまうので禁止)。既にjunctionならリンクのみ外して張替
  (junction削除は `Delete()` でリンクのみ除去。`Remove-Item -Recurse`
  はPS5.1でリンク先実体を巻き込む危険があるため使わない)。
  `python/plugins/<id>` が `qgis-plugin/<id>` へのjunctionになり、
  repo編集がそのままQGIS側のディスク内容になる
  (import済みモジュールは `reload_plugin` / `live:devreload` で反映)。
  junction作成に失敗した場合も **自動でcopyには落とさずエラー**とする
  (deploy-plugin.ps1 の仕様。静かなcopy化を防ぐため)
- **利用モード(use) = 退避版の復元(UI操作のみ)**:
  `npm run deploy:use` のみが切り替える。junctionを外し、
  **`qgis_live_parked/<id>` の退避版があれば復元する(repo copyしない)**。
  退避も既存実体も無ければ未配置のまま(=そのプラグインは
  利用されていなかった、という意味)。つまり利用版の中身は常に
  「過去にインストール/退避されたもの」で、開発サイクルを往復しても
  上書きされず保全される — 「開発を終えて戻る = 保存した利用版に戻る」。
- **利用版の新規配置・更新 = `npm run deploy:install`(`-Install`)**:
  repoの現状を利用版としてcopyするリリース操作(UI操作のみ)。
  junctionを外し、旧parkedは破棄して新しいcopyを配置する。
  「利用版を確定コードに更新したい」時はこの経路だけを使う
  (確定 → `git commit/tag` → `deploy:install` で利用版=正式版として追跡可)。
  copyを生成する自動経路は意図的に存在させない。
  開発へ戻るには `npm run deploy` を明示実行する
  (parkedは plugin ごとに記録され、`deploy:status`/`deployMode()`/
  Deploy Modeダイアログに `(+parked)` として表示される)

#### 【重要】利用モード中はプラグイン内容を一切更新しない

不用意な変更が運用の支障になるため、利用モードでは
**あらゆる経路でプラグインの内容(配置ファイル・実行コード)を
変えない**ことを保証する:

- **ファイル配置**: junctionが存在せず実体dirは物理的に不変。
  repo編集は利用環境へ届かない
- **自動deployは存在しない**: `live:ensure`/`live:reload`/`test:live`
  はQGIS起動/接続のみ行い、配置変更のコード経路自体を持たない。
  配置済み実体dirのままQGISを起動/アタッチする(=リリース版を
  そのまま実環境で検証できる)
- **起動時のdev機構**: harness起動でも `WEBENGINE_DEV_SRC` を
  立てない(repo側コードが実行時に混入しない)
- **QGIS内リロード系**: `reload_plugin` は配置済み実体dirを
  再importするだけで内容は不変。ドライバのホットリロードメニューは
  junction配置のみを候補にするため use では候補自体が出ない
- **内容を変えられるのはUI操作のみ**:
  `npm run deploy`(dev切替。利用版はparkedへ保全)/
  `deploy:use`(use切替=parked復元。無ければ未配置のまま)/
  `deploy:install`(リリース=repo現状を利用版として配置)

この保証に反する新規コード経路(プラグイン配置物を書き換える・
repo側コードをimportする・deployを呼ぶ処理)は追加しないこと。

注意: プロファイルは共有(開発QGISも通常起動QGISも同じ `python/plugins/`
を見る)ため、**開発モード中**は通常起動のQGISにもrepoのコードが載る。
これは「開発中はrepo優先」の意図通り。利用モードではjunctionが
存在しないため、人が普通にQGISを起動しても確定の実体dirで動く。

### 選定理由(共有プロファイルを採る理由)

プロファイル完全分離(`--profile` でdev専用プロファイル化)も検討したが、
**この環境の目的が「実務利用環境での正確な動作確認」であるため共有を選んだ**:

- **環境忠実度が最大**: 接続設定(PostGIS/WMS等)・認証・共存プラグイン・
  QGIS4.ini設定まで検証環境と利用環境が物理的に同一になる。
  別プロファイルは設定差分が「devでは動くが実務では動かない」
  原因になり得る
- **配布形態の再現も可能**: `deploy:install`/`deploy:use` で「インストール済み状態」を
  同一プロファイル内で再現でき、junction(開発中)と実体dir(配布形態)を
  同じ環境で切替検証できる
- 分離の主な利点(利用側の保護・設定汚染防止・同時起動の干渉回避)は、
  **この環境自体が検証対象**である運用では価値が薄い

共有の代償として受け入れる点:

- 開発モード中は利用側にもrepo WIPコードが載る(`deploy:use` の
  利用モード切替で対処。実体配置はUI操作のみ、use中は自動deployも
  抑制されるため、気づかないうちにモードが変わることはない)
- 複数インスタンスの同時起動はQGIS4.iniがlast-writer-wins
  (意図の違うインスタンスを長時間並走させない)
- junction作成に失敗する環境では開発deploy自体がエラーになる
  (copyへ自動フォールバックはしない)。その場合は運用者判断で
  `deploy:use`/`deploy:install` を使うが、repo編集は届かない点に注意

将来「利用側を開発事故から守りたい」需要が出た場合は、
`deploy-plugin.ps1 -Profile` + `qgis-bin.exe --profile` の
明示指定でプロファイル分離へ移行できる(現行スクリプトは
lastProfile自動検出のため、分離時は両者に `-Profile`/`--profile`
の明示が必要)。

```powershell
# QGIS常駐インスタンスを用意(起動済みならアタッチ、未起動なら起動を自動化)
npm run live:ensure
#   → live dirが応答すれば再利用、無ければ
#     WEBENGINE_DEV_SRC等(devモード時のみ)のenv付きでQGISを起動して
#     LiveDriver応答までポーリング。deployは一切しない(未配置なら
#     先に npm run deploy / deploy:install を手動で)

# ★普段のコード反映はこれだけ。bridge.py/logic.py/ui/* の変更を即反映。
#   deployもreloadPluginも再起動も不要
npm run live:devreload
#   → repo側の qgis-plugin/<id>/ を別名パッケージ(<id>_devsrc)として再importし、
#     WebChannelのbridgeオブジェクトを差し替えてページを再読み込みする

# プラグインの器側(main_plugin.py, live_driver.py等)を変更した時だけこちら
npm run live:reload     # = pyevalで sys.modules掃除+reloadPlugin
#   + open_dialog し直し(deployはしない。junction配置ならrepoコードが反映される)

# ★ホットリロード(watchモード): qgis-plugin/<id> の保存を監視して自動反映
npm run live:watch      # 起動中は編集→保存だけでリロードされる(Ctrl+Cで終了)
#   ui/**・bridge.py・logic.pyのみの変更かつ対象がview持ち → devreload、
#   それ以外(本体*.py等を含む) → reload_plugin を自動選択。
#   --plugin <id> で対象絞込、--debounce <ms> でまとめ待ち調整可
#   (junction配置前提。利用モード(実体配置)ではrepo編集が届かないため
#    先に `npm run deploy` でjunction化すること)
# ※QGIS側メニュー「QGIS Live Driver > ホットリロード」からは対象プラグイン
#   (qgis-plugin/ 内のもののみ)を手動選択してreload_pluginできる(自動watchなしの手動版)

# 実QGIS内UIを検証(QGIS未起動でも内部でensureして自動起動)
npm run test:live       # test-results/qgis-live.png にスクショも残る

# 手動で個別に回したい場合の旧手順も引き続き使える
npm run deploy          # プラグイン配置(junction固定、失敗時はエラー)
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

## 国際化(i18n)/多言語化(固定方針)

**qgis-plugin/ 下の全プラグインは英語をソース言語とし、
`i18n/<lang>.json`(JSONカタログ)方式に統一する。
.ts/.qm/Qt Linguist(lupdate/lrelease)・言語別のPython辞書等、
他の翻訳方式は使わない。**

- **採用言語(固定・全プラグイン同一)**: ソース言語=英語(en)で
  カタログ不要。翻訳対象は次の9言語のみ:
  ja・de・es・fr・it・pt・ru・zh・hi
  (9言語以外のカタログは置かない。過去に存在した geo_import の
  fi/en、geo_report の en は廃止済み — git履歴から復元可能。
  追加する場合は全プラグインへの展開が前提)
- **カタログ**: `<plugin>/i18n/<lang>.json`(UTF-8)の
  `{"<context>": {"<英語ソース>": "<翻訳>"}}` 2層JSON。
  キーの追加・修正は **JSONを直接編集するだけ**。ビルド・コンパイル・
  Qt Linguist 等のツールは一切不要(AIが直接読み書きできる
  テキスト形式が正)。未登録のソースは実行時に英語へフォールバック
  するため、未翻訳のまま置いても動作する
- **ローダ**: 各プラグインに同一内容の `i18n_json.py` を置き、
  起動時に `self.translator = install_translator(PLUGIN_DIR)` を呼ぶ
  (返り値の参照保持は必須)。中身はJSON辞書を引く QTranslator
  サブクラスで、`QCoreApplication.installTranslator` するため
  `self.tr()`/`QCoreApplication.translate()`/`QT_TRANSLATE_NOOP`/
  `.ui`(uic/loadUi経由)の全経路が同じカタログを引く。
  言語判定は `locale/userLocale` → `QLocale.system()` の順
- **ソース言語は英語**: UI文字列・ログ・ユーザー向けメッセージは
  コード内では英語で書く。`.ui` ファイルの文字列も英語。
  マーキングは Qt 標準の `self.tr("...")` /
  `QCoreApplication.translate("<ctx>", "...")` /
  `QT_TRANSLATE_NOOP` のみ。**カスタムの `tr()` ラッパーは
  コンテキスト名がカタログとずれる原因になるため禁止**
  (translate第1引数=context名をコードとJSONで一致させる。
  context不一致時は全context検索にフォールバックするが、
  同名ソースの別訳を拾い得るため基本は一致させる)
- **Qtを介さない文字列**(生成HTML等): `i18n_json.translate_text()`
  または `catalog()`/`lookup()` で同一カタログを直接引く
  (実装例: geo_webview の "geo_webview.page" context)
- **日本語は翻訳・ドキュメントとして維持**: UIの日本語は
  ja.json の翻訳として提供し、日本語ドキュメントは
  `README_JP.md` 等として `README.md`(英語)と併存させる
  (upstreamが日英併記README形式を持つプラグインはその形式を維持してよい。
  README等のドキュメント翻訳はja以外は必須としない)
- **翻訳しないもの**: 保存済み設定値・プロジェクト変数名・フィールド名・
  API値・フォーマット種別等のデータドメイン文字列・内部識別子・
  URLスキーム・外部プロトコル値。表示用文字列とセンチネル/キー値は
  必ず分離する(例: 表示「All」と比較値の一致を translate 経由で保証)
- **検証・変換ツール** (`scripts/i18n_tool.py`):
  - `check [plugin_id]`: ソース(.pyのtr/translate/QT_TRANSLATE_NOOPと
    .uiの`<string>`)を走査し、カタログ未登録のキーを報告
    (新規文字列追加時に追記漏れが無いか確認する)
  - `convert [plugin_id]`: upstreamから.tsを取り込んだ場合に
    `<lang>.json` へ変換する(.ts側はコミットしない)
- **制限**: numerus(複数形)は先頭の訳文のみ使用する簡易仕様
- 翻訳カタログの変更は他の機能変更と同様に **プラグインの
  CHANGELOG.md に記録し metadata.txt の version も上げる**

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
