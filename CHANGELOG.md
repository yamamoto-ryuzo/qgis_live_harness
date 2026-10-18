# Changelog

このプロジェクトの注目すべき変更はすべてこのファイルに記録します。
フォーマットは [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/)、
バージョニングは [Semantic Versioning](https://semver.org/lang/ja/) に準拠します。

## [Unreleased]

## [1.2.0] - 2026-10-18

### Added

- **メニュー「ホットリロード」**(qgis_live_driver 0.9.0、
  `hot_reload.py`): 「プラグイン > QGIS Live Driver >
  ホットリロード」サブメニューから開発対象
  (plugin.config.jsonのid)を選んで手動reloadPluginする。
  QGIS再起動・deploy不要の手動ホットリロード
- **開発中ホットリロード `npm run live:watch`**(`scripts/live-watch.mjs`):
  `plugin.config.json` の全idを `qgis-plugin/<id>/` 配下で監視し、
  ファイル保存のたびに実行中QGISへ自動反映するwatchモード。
  `ui/**`・`bridge.py`・`logic.py` のみの変更かつ対象がWebEngine
  viewを持てば `devreload`、それ以外(本体 `*.py`/`.ui` 等を含む)は
  `reload_plugin` を自動選択して送信する。debounce(既定500ms)で
  連続保存をまとめ、変更が複数プラグインに跨る場合は制御面の
  `qgis_live_driver` を最後にリロード。`--plugin <id>` で監視対象の
  絞込、`--debounce <ms>` で待ち調整が可能。QGIS未起動なら
  ensureで自動起動し、コマンド消失系の失敗時はensureして1回リトライ。
  junction配置が前提(-Copy配置は先に `deploy:copy`)
- **upstreamプラグイン4件を `qgis-plugin/` に組み込み**:
  `geo_report`(yamamoto-ryuzo/geo_report)・`geo_import`(geo_import)・
  `QGIS-legendView-main`(QGIS-legendView、repoルート=プラグイン構造を
  そのまま配置)を実体git管理で取り込み、`plugin.config.json` の id 配列に
  追加して test:live/live:reload の検証対象にした。
  geo_report/geo_importは `C:\devin/<repo>` にcloneしてプラグイン
  subfolderをここへのjunctionに置換。「repoルート=プラグイン」構造の
  QGIS-legendView/QGIS-exportExcelは upstreamの `.git` を
  `.upstream/<repo>.git` に退避し `core.worktree` を `qgis-plugin/<id>` に
  向けるgitdir運用にした。いずれもHarness側が正本で、upstream操作は
  `npm run upstream -- <repo> <git引数>`(scripts/upstream-git.ps1)が
  clone/gitdir両形式を吸収する。
  さらに **`geo_excel`** を新設: `QGIS-exportExcel` のレイヤアクション
  用スクリプト群(metadata.txtを持たない非プラグイン)を簡易プラグイン化し、
  プラグインメニューからアクティブレイヤ/選択地物へ実行可能にした。
  スクリプト本体は無改変で同梱し、`[% @layer_id %]`/`[% $id %]` を
  実行時置換、PyQt5固定importはexec直前のソース書き換えで
  `qgis.PyQt` に変換(Qt6対応)。
- **管理プラグイン全件のAI制御フル対応**: `geo_report`・`geo_import`・
  `QGIS-legendView-main` にも `bridge.py`(`GeoReportBridge`/
  `GeoImportBridge`/`LegendViewBridge`)を新設し `plugin.bridge` に配線。
  `bridge_call`/`describe_plugins` から利用可能(geo_search・geo_webview・
  geo_excelは既対応。repo管理プラグインはbridge.py+pluginInfo標準スキーマが
  前提になった — AGENTS.md参照)。各種modalダイアログはbridge経路では
  自動応答/パス指定直読みで吸収し、呼出をブロックしない
- **管理プラグイン全件をQGIS4以降専用に更新**: 残っていた
  `qgisMinimumVersion=3.40` を全件 `4.0` に統一
  (`geo_excel` 1.3.0 / `geo_import` V2.5.0 / `geo_report` 2.4.0 /
  `geo_webview` 3.12.0 / `QGIS-legendView-main` 2.2.0。
  geo_search・qgis_live_driverは既に4.0起点)。
  併せて全プラグインの `homepage`/`tracker`/`repository` を
  upstream個別repoから Harness repo の `qgis-plugin/<id>` 配下
  (tree/master)・issues に統一(正本はHarness側のため)。
  author を `yamamoto-ryuzo` に統一し、ライセンスをGPL-3.0
  (geo_importのみMIT継続)に統一。`QGIS-legendView-main` はQt5
  対応コードを完全削除してQt6専用化、`plugin.config.json` に
  `geo_excel` を追加して全管理プラグインを検証対象にした
- **管理プラグイン全件のQt5/フォールバック残存を一掃**: 実機QGIS4では
  非スコープenum(`QMessageBox.Yes`/`Qt.UserRole`/`QHeaderView.Stretch`等)は
  属性エラーになるため、全プラグインの残存Qt5分岐・enum shim・
  `exec_()`・動的enum解決(getattr/`hasattr`フォールバック)を削除し
  Qt6スコープenumに統一。`geo_import/update_translations.py` は
  pylupdate6専用に、`resources_rc.py` のPyQt5由来ヘッダーも整理。
  `QGIS-legendView-main` の旧upstream文書 `README.txt`/`README.html` を削除。
  `geo_import` CHANGELOG/metadataの `V` 接頭辞を全エントリで除去
  (geo_excelのupstreamスクリプト内 `PyQt5` 記述は exec直前の
  ソース書き換え設計として意図的に維持)
- **bridge未搭載プラグインへの汎用アダプタ**(`qgis_live_driver` 0.5.0):
  `live_driver._GenericBridge` が `plugin.bridge` を持たない
  プラグイン(mmqgis等のサードパーティ製含むロード済み全件)に
  `pluginInfo`/`status`/`actions`/`trigger`/`run`/`openDialog`/
  `closeDialog` を提供。`run`/`trigger` はQTimer.singleShotで
  非同期発火するためmodalダイアログを開いても応答をブロックしない。
  `describe_plugins` では `generic: true` としてmetadata由来の
  自己記述が載る。また `qgis_live_driver` 自身にも
  `bridge.py`(`QgisLiveBridge`)を配線しカタログに自己記述を追加
- `geo_excel` に **AI向けブリッジ**(`bridge.py` の
  `GeoExcelBridge`)を追加し `plugin.bridge` に配線。
  `bridge_call` / `describe_plugins` から `listScripts` /
  `layerVariables` / `setLayerVariables` / `run` / `status` を
  呼べる。`run` はスクリプト内のmodal QMessageBoxを実行中だけ
  自動応答(confirmで上書き/続行Ok、既定は中断)に差し替え、
  `excel_result`/`output_path` を構造化して返す
- **プラグイン個別の文書管理**を開始。`qgis-plugin/<id>/` 配下に
  各プラグインの README/CHANGELOG/詳細文書を配置する方式に統一。
  `geo_search`: upstream(GEO-search-plugin)から README.md /
  README_JP.md / SEARCH.md / SEARCH_JP.md / THEMES.md /
  THEMES_JP.md / CHANGELOG.md を復元し V4.1.0(bridge追加)を追記、
  metadata 4.1.0へ。`geo_webview`: upstreamから README.md /
  README_JP.md / SPEC.md / SPEC_JP.md / CHANGELOG.md を復元。
  `qgis_live_driver`: CHANGELOG.md 新設、metadata 0.4.0へ
- **AI向けプラグインカタログ**(`describe_plugins` コマンド):
  「どのプラグインをいつどう使うか」をAIが発見するための集約機構。
  `qgis_live_driver` がロード済み全プラグインを列挙し、bridgeを持つ
  ものは各 `pluginInfo()` の自己記述(標準スキーマ:
  `id/name/summary/when_to_use/invoke/methods[{name,signature,
  description,example}]/state`)を集約して返す。ファイルJSONL /
  REST `/api/cmd`・`/api/tools` / MCP `qgis_describe_plugins`
  (qgis-mcp.mjs・プラグイン内蔵 `/mcp`・`mcp_stdio.py` の全面)で
  公開され、QGIS内AIアシスタントパネルからも利用できる。
  `status` のプラグイン情報に `bridge` フラグを追加。
  `geo_search.bridge.pluginInfo()` はこの標準スキーマで実装済み
  (methodsは `inspect.signature`+docstring自動生成+`METHOD_DOCS`補足)
- `geo_search`: **AI/外部制御用ブリッジ**(`bridge.py` の
  `GeoSearchBridge`)を追加し `plugin.bridge` に配線。
  `qgis_live_driver` の既存 `bridge_call` コマンドが
  `plugins['geo_search'].bridge.<method>(*args)` をプロセス内で直接
  呼ぶため、ファイルJSONL / REST `/api/cmd` / MCP `qgis_bridge_call`
  (AIアシスタントパネル含む)の全経路から利用できる。
  WebChannel不要のQt Widgetsプラグイン向けの第一級制御面。
  メソッド(JSON文字列返却): `pluginInfo` / `status` / `listTabs` /
  `selectTab` / `search` / `results` / `zoom` / `openDialog` /
  `closeDialog`。`search(query, tab, show, zoom, max_features)` は
  検索ボタン押下と同じ `show_features` 経路を通り、結果を
  `result_dialog._tabs` から構造化(レイヤ別・属性・centroid)して返す。
  query は str(先頭入力欄) / list(各入力欄) /
  dict({フィールド名 or ViewName or 表示ラベル: 値}) を取る。
  実QGISでメモリレイヤ検索・全レイヤ検索・dictクエリを検証済み。
  さらに全機能をカバーするメソッドを追加:
  `searchOptions`(pan_mode/fixed_scale/show_layer_name) /
  `tabOptions`(地番=完全一致|あいまい・字コード選択、所有者=対象
  フィールド・一致方式) / `suggest`(ユニーク値) /
  `listThemes`・`applyTheme`・`themeAdditive`(マップテーマ) /
  `saveUserTheme`・`loadUserTheme`(ユーザーテーマJSON) /
  `getSettings`・`setSettings`(geo_search_json) /
  `tabSetting`・`addTabFromCurrentLayer`・`removeTab`・
  `reloadDialog`(タブ管理・設定由来を跨ぐ削除・再構築)。
  `search` に `options` 引数を追加(検索前にオプション適用可能)
- `qgis_live_driver` 0.3.0: **AIアシスタントパネル**を追加。
  `プラグイン > QGIS Live Driver > AI アシスタント` で開くチャット型
  エージェントドック(Qt Widgets)。**OpenAI互換API**
  (`{base}/chat/completions` + function calling)と **Gemini API**
  (`{base}/models/{model}:generateContent` + functionDeclarations)
  をプロバイダ選択で接続し、モデルが `mcp_http.TOOLS` と同じツール群を
  `driver.submit()` 経由でループ実行する。リモート制御OFFでも
  パネル専用の内部ドライバで動作
  (`ai_panel.py` / `ai_client.py`、stdlibのみのクライアント層は
  pytest対象)。APIキーはOS資格情報ストアに保存する
  (`credential_store.py`: Windows=DPAPI / macOS=キーチェーン /
  Linux=Secret Service、無い環境は600権限ファイルにフォールバック。
  ストア書込み失敗時は平文保存せずエラー表示)。
  モデル欄は編集可コンボ+「取得」ボタンで `GET {base}/models` から
  モデル一覧を取り込める
- AIパネルのモデル一覧を**種別グループ化+価格表示**に改善。
  「テキスト(画像入力可)/テキスト/画像生成/埋め込み/その他」の
  見出し付きでドロップダウンを構成し、各項目に参考価格
  (入力/出力, $/1Mトークン)を併記・ツールチップで詳細表示。
  価格はOpenRouter等が返す `pricing`/`context_length`/`modality`
  を優先利用し、無ければ主要モデルの既知価格表(参考値)に
  フォールバック。既定エンドポイント利用時は「取得」不要の
  推奨モデル一覧を予め表示する
- `scripts/qgis-mcp.mjs`: 死んだQGISインスタンスの残骸live dirへ
  コマンドを振ってしまう不具合を修正。`liveDirs()` が1件応答で
  全dirを返していたのを、応答したdirのみ返すよう変更

### Removed

- `geo_search` の未使用コード・不要ファイルを整理。
  未参照ファイル `autodialog.py`・`resources.py`/`resources.qrc`・
  `view.sql`・`setting.json.sample`・`i18n/*.ts`(翻訳ソース。
  実行時は`.qm`のみ使用)を削除。デッドコードとして
  `save_tab_config`(searchdialog)、`set_form`(resultdialog)、
  `open_feature_form`/`zoom_item`/`add_search_task`/`search_task`/
  `search_finished`(searchfeature、QgsTask非同期検索の未配線経路)、
  `export_themes_dialog`/`import_themes_dialog`等(settingsdialog、
  ボタン自体が撤去済みで到達不能)、`_set_obj_state`(theme)、
  未使用の`_set_current_value`/`_set_current_scale`クロージャ、
  各ファイルの未使用import(`NULL`/`IsNot`/`nullcontext`/`Qt`/
  `QDialog`/`QInputDialog`/`QComboBox`/`iface`/`types`/`Optional`等)を除去
- `geo_webview` の未使用コード・不要ファイルを整理。
  `i18n/*.ts`(翻訳ソース。`.qm`不在で実行時には使われない)・
  `icon_org.png`・`__pycache__` を削除。デッドコードとして
  panel.py の MapLibreボタン冗長配線(plugin側の
  `on_maplibre_clicked_panel` と二重接続になり、かつ存在しない
  `qmap_maplibre` モジュールへのimport失敗でボタンが無効化されていた)、
  `update_google_buttons_state`、plugin.py の `my_custom_function`・
  `qgsfunction`・`QgsMapCanvas` import・Google Earth補助の未呼出メソッド群
  (`_zoom_to_earth_distance`/`_extract_altitude_from_earth_url`/
  `_estimate_ground_resolution_from_altitude`/
  `_compute_scale_from_map_width_with_dpi`)・無効化済みテーマ検出
  (`_get_current_theme_info`/`_get_current_layer_states`/
  `_detect_current_theme`)、server_manager.py の重複・未呼出メソッド
  (先勝ちでshadowされていた `_build_navigation_data_from_params` 初版、
  wms_service側に同名実装がある `_get_canvas_extent_info`/
  `_handle_permalink_as_wms_getmap` のコピー、`_get_ol_proj_head`/
  `_crs_has_proj4`/`_set_canvas_extent_from_bbox`/`get_last_request`)、
  `export_layer_geojson`/`export_mapbox_style_json`(maplibre_generator)、
  `sld_to_mapbox_style`/`_extract_css_param`(qmap_maplibre_wfs)、
  `default_wmts_layers_js`(qmap_maplibre_wmts)、
  `estimate_scale_from_zoom_maplibre`(scale_zoom)、
  `escape_js_string`/`get_qgis_layers_info`/`get_current_extent_info`/
  `_resolve_coordinates`(webmap_generator)、`_extract_style_hint`
  (wfs_service)、`_apply_label_rotation_correction`(wms_service)、
  `get_identity_diagnostics`(wmts_service)、各ファイルの未使用importを除去

### Fixed

- `geo_webview` server_manager の遅延サービス生成が存在しない
  `.qmap_wmts_service`/`.qmap_wfs_service` をimportして常に失敗して
  いたのを、実在する `.wmts_service`/`.wfs_service` に修正

### Removed

- **サンプルプラグイン `webengine_plugin` を削除**(`qgis-plugin/webengine_plugin/`)。
  併せてその固有テスト(`tests/e2e/plugin-ui.spec.ts`、`tests/unit/test_logic.py`)と
  テンプレート生成スクリプト `scripts/new-plugin.mjs`(`npm run new:plugin`)を除去。
  `plugin.config.json` の既定idは `qgis_live_driver`。L1基盤
  (`playwright.config.ts`/`serve-ui.mjs`)は残置(WebEngineプラグイン追加時に
  specを再作成すれば再利用可)

## [1.1.0] - 2026-10-18

### Added

- `scripts/setup.ps1`(`npm run setup`): 初回クローン後の一括セットアップ。
  前提ツール(QGIS 4.x / Node.js 24+ / Python 3.13+ / pytest)を確認し、
  不足分をwinget経由でインストールした上で `npm install` →
  `npx playwright install` → `npm run deploy:copy` を実行する
  (`-Yes` / `-CheckOnly` / `-SkipPlaywright` / `-SkipDeploy`)

## [1.0.0] - 2026-10-18

初回公開リリース。QGISプロセスをAI/外部スクリプトから自律駆動するための
開発・制御・検証基盤 **QGIS Live Harness**(このリポジトリ)と、QGIS内に常駐する
制御プラグイン **QGIS Live Driver** を含む。

同梱プラグインはリポジトリとは別のバージョン系で管理する:

- `qgis_live_driver`: 0.2.0 (experimental)
- `webengine_plugin` (サンプル): 0.1.0 (experimental)

### Added

- **QGIS Live Driver** (`qgis-plugin/qgis_live_driver`): QGIS内で動く制御専用プラグイン
  - ファイルJSONL(`commands.jsonl` → `results.jsonl`)によるコマンド実行
    (`eval` / `pyeval` / `screenshot` / `devreload` / `status` /
    `open_plugin` / `reload_plugin` / `bridge_call`)
  - REST `/api/*` と MCP Streamable HTTP `/mcp`(127.0.0.1バインド)、
    同梱stdio shim `mcp_stdio.py`(Node不要)
  - `plugin_id` ルーティング(hub): 1つのlive dir/HTTPポートから
    live中の全プラグインを制御
  - セキュリティ: 全チャネルでセッショントークン認証必須、Host/Originの
    loopbackチェック、`QGIS_LIVE_API_KEY` / `QGIS_LIVE_TOOLS` env、
    QSettings永続化のリモート制御トグル(既定オフ・初回警告付き)
- **QGIS Live Harness**(リポジトリ基盤)
  - `scripts/live-drive.mjs` (`LivePage`): Playwright相当の
    evaluate / pyeval / screenshot / waitFor / click / devreload 等のクライアントAPI
  - `scripts/qgis-session.mjs`: ensure(起動中へのアタッチ/自動起動) /
    reload / devreload
  - `scripts/qgis-mcp.mjs`: 上記経路をMCPツールとして公開するstdioサーバ
    (`qgis_ensure` / `qgis_pyeval` / `qgis_eval` / `qgis_bridge_call` /
    `qgis_screenshot` / `qgis_status` / `qgis_open_plugin` /
    `qgis_devreload` / `qgis_reload`)
  - `npm run live:*` / `test:live` / `deploy` / `new:plugin` コマンド群
  - 複数QGISインスタンス・複数プラグインのlive dir分離
    (`qgis-<pid>/<plugin_id>`)
  - `plugin.config.json` による開発対象プラグイン切替、
    `scripts/new-plugin.mjs` によるプラグイン雛形生成
- **サンプルプラグイン** `webengine_plugin`: QWebEngineView + QWebChannel
  bridge構成の雛形(mock-bridgeによるQGIS無しのUI単体動作付き)
- **検証基盤**: L1 Playwright(`npm test`)、pytest(`tests/unit`)、
  実QGIS検証 `test:live`
- **ドキュメント**: GitHub Pages用 `docs/`(概要 / 使い方 / セキュリティ /
  Driver / Harness / 配布 / internals)、AGENTS.md、SECURITY.md、
  THIRD_PARTY_LICENSES.md
- ライセンス: GPL-2.0-or-later

### Fixed

- `mcp_stdio.py` の serverInfo バージョンを `mcp_http.py` / metadata.txt に
  合わせ 0.2.0 に修正

[Unreleased]: https://github.com/yamamoto-ryuzo/qgis_live_harness/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/yamamoto-ryuzo/qgis_live_harness/releases/tag/v1.2.0
[1.1.0]: https://github.com/yamamoto-ryuzo/qgis_live_harness/releases/tag/v1.1.0
[1.0.0]: https://github.com/yamamoto-ryuzo/qgis_live_harness/releases/tag/v1.0.0
