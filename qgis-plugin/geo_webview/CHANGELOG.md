# 変更履歴(Changelog)

このファイルでは geo_webview プラグインの主な変更点を記録します。

記法は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に基づき、
[Semantic Versioning](https://semver.org/spec/v2.0.0.html) に準拠します。

## バージョン形式: VA.B.C

- **A**: QGIS コア更新やプラグインアーキテクチャ大幅変更などのメジャー変更
- **B**: UI 変更・新機能追加・中規模な機能拡張
- **C**: 軽微な不具合修正・小改善・プロファイル/プラグインの微修正

## [4.6.0] - 2026-11-07

- マップテーマのスタイル再現を強化: テーマが記録するレイヤー別の
  名前付きスタイル(MapThemeRecord.LayerRecord.styleName)を
  `DATA/<slug>__<theme>.qml` として出力し、`theme:` 行の該当タイトルに
  `;style=` を付与する。QGIS でテーマ別にスタイルを切り替えている
  プロジェクトを Canvas 側でも再現できる(kasugai_canvas 側が
  テーマ適用時に .qml を差し替え)
- .kasc 行と出力ファイルの紐付けは従来どおり slug 規則
  (`<slug>__<theme-slug>.qml`)

## [4.5.0] - 2026-11-07

- KASUGAI Canvas 連携エクスポートの再現度を強化(kasugai_canvas Issues #49-61 対応):
  - 時間対応レイヤ(QgsTemporal)を `time=`/`time_end=` オプションへ自動出力(#57)
  - ベクターレイヤの不透明度を `opacity=` として全ベクター行へ出力(#58)
  - レイヤ/地物ブレンドモード・未対応レンダラ(2.5D/反転ポリゴン/
    ジオメトリジェネレータ等)を warnings へ明示(#54/#58)
  - ヒートマップ/ポイントクラスタ/ポイント変位レンダラを Canvas 側の
    `heat=on`/`cluster=on` へマッピング(#54)
  - WMTS レイヤ(tileMatrixSet を持つ wms ソース)を `wmts:` 行として出力(#51)
  - 非GeoTIFFラスタ(JPEG/PNG/VRT/IMG/SDAT/GRIB 等)と再現不能なレンダラ設定
    (疑似カラー/ヒルシェード/ストレッチ/パレット)を QGIS で描画済み PNG へ
    焼き付け `image:` 行として出力(#52/#53)。multibandcolor のバンド選択は
    `bands=` として出力
  - 対象外レイヤ種別(メッシュ/ベクタータイル/点群/アノテーション/
    プラグイン/グループ)の skipped 理由を和訳で明示(#50)
  - レイヤーツリー詳細状態: グループ折りたたみを `group:` 行、
    カスタムレイヤー順(hasCustomLayerOrder)を行順で出力(#59)
  - 保存済み3Dビューを `cam:QGIS3D <名前>` 行(dist/pitch/yaw→位置・姿勢逆算)
    と `terrain:` 行(垂直誇張)として出力(#60)
  - プロジェクト保存時の自動再エクスポートを追加(#61)。
    QSettings `kasugai_auto_export` を true にすると projectSaved 直後に
    kasugaiExport(open_app=True) 相当を遅延実行し Canvas へ即時反映

## [4.4.0] - 2026-11-07

- レイヤの「縮尺による表示」設定（`hasScaleBasedVisibility` +
  `minimumScale`/`maximumScale`）を `.kasc` 行へ `| minScale=` / `| maxScale=`
  として出力するようにした。ベクター（geojson/gpkg/geoparquet/flatgeobuf/
  duckdb）、3dtiles、xyz/base、wms、geotiff の全レイヤ行が対象。
  KASUGAI Canvas 側で QGIS と同じ縮尺範囲（minScale=引き側限界→ズーム下限、
  maxScale=寄り側限界→ズーム上限）の表示/非表示として再現される。

## [4.3.0] - 2026-11-07

- GDAL ラスタレイヤ（GeoTIFF/COG）を `geotiff:` 行として `.kasc` に出力するようにした。
  ローカルの `.tif`/`.tiff`/`.gtif` は `DATA/` へ複製して相対参照し、
  `http(s)`/`/vsicurl/` の COG URL はそのまま参照する。
  レイヤ不透明度は `opacity=` へ、出典は `attr=` へ引き継ぐ。
  再生は KASUGAI Canvas（Cesium エンジン）の geotiff.js デコードで行い、
  EPSG:4326/3857 はタイル LOD、それ以外の座標系は四隅再投影のオーバーレイ描画となる。
  これまでは XYZ/WMS/3dtiles 以外のラスタがスキップ対象だった

## [Unreleased]

- `.kasc` 既定ベースマップ群の `淡色地図`/`全国最新写真`（GSI `pale`/`seamlessphoto`）に
  `minZoom=2` と `bbox=122,19,155,47` を追加。両タイルはズーム 2 未満および
  日本周辺の範囲外が存在せず、Canvas 側で global 表示時に大量の 404 タイル要求が
  発生していた（Cesium エンジン側でも `base:` 行の `minZoom`/`bbox` 解釈を実装済み）

## [4.2.2] - 2026-11-07 Canvas 連携のループバックアドレスを 127.0.0.1 へ統一

- Canvas 検出・登録・コマンド送信・生成URL の接続先を `localhost` から
  `127.0.0.1` へ統一。Canvas 本体・バックエンド検出・起動HTMLは
  一貫して `127.0.0.1:8510` を使う設計のため、`localhost` が `::1` 優先で
  解決される環境で `[::1]:8510` の無関係なサービスへ接続してしまい、
  検出失敗→`via: qgis-http` への静かなフォールバックが発生し得た
  （`detect_kasugai`/`register_kasugai_project`/`kasugai_command`/
  `build_kasugai_url`/`build_local_view_url`/`build_hosted_view_url`）
- 併せて Canvas 側(web/)も修正: `switchProject` がページ読込後に
  `/api/projects/register` で登録された外部プロジェクトを一覧未反映で
  「プロジェクトが見つかりません」としていた問題を解消
  （切替前にマニフェスト再読込するよう各エンジンで対応）

## [4.2.1] - 2026-11-06 未読込・破損レイヤのエクスポート対応

- `.kasc`+`DATA/` エクスポート(`export_kasugai_project`)で、レイヤツリー上
  `layer()` が `None` の未読込レイヤを黙って落としていた問題を修正。
  `_tree_layers()` がプロジェクトファイル(.qgs/.qgz)内の `<maplayer>`
  定義を layerId で照合して `readLayerXml` で再生成・再登録
  (スタイル等のプロジェクト設定も復元)し、layerTreeRegistryBridge/
  `resolveReferences` でノードへ解決させて本来のツリー位置で出力する。
  解決不能なものは skipped に「(未読込レイヤ)」として記録
- `isValid()` が False の破損レイヤ(読込時にソース未達等)も
  `setDataSource` で同一ソースの再オープンを試みる。復旧できたものは
  warnings に「破損レイヤを再読込」、不能なものは skipped に
  「(破損レイヤ)」として記録

## [4.2.0] - 2026-10-28 GSI Maps エンジン対応

- KASUGAI Canvas の `gsimaps`(地理院地図)エンジンを起動エンジンの
  選択肢に追加(`VALID_ENGINES`・`normalize_engine`)
  - `GET /kasugai?engine=gsimaps`・bridge `kasugaiExport`/`openExternal`・
    `setSettings(kasugai_engine)`・パネルの `Engine:` コンボで選択可
  - エクスポート時に `gsimaps.html` 起動ページも生成
    (`_LAUNCHER_ENGINES` に追加、`index.html` のエンジン一覧にも掲載)
- README/SPEC(英・日)/metadata.txt のエンジン列挙を5エンジンへ更新
- 内蔵 HTTP サーバーの CORS を許可リスト方式へ強化: 全応答で
  `Access-Control-Allow-Origin: *` を返していたのを、file://(null)・
  ホスト版エンジン(github.io・設定のカスタムURL)・ループバックの
  オリジンのみへエコーに変更。OPTIONS の Private Network Access 応答も
  許可オリジンのみ返し、任意サイトからのローカルデータ読み取りを遮断

## [4.1.0] - 2026-10-28 印刷レイアウト PDF 出力エンドポイント

- 内蔵 HTTP サーバーに印刷レイアウト関連の2エンドポイントを追加
  (KASUGAI Canvas 印刷ダイアログの「QGISレイアウトでPDF出力」が利用):
  - `GET /layouts` — プロジェクトの印刷レイアウト一覧を JSON で返す
    (`{ok, layouts:[{name,pages,w_mm,h_mm}]}`)
  - `GET /layout-pdf` — `QgsLayoutExporter` で印刷レイアウトを PDF 出力。
    `?layout=<name>` 省略時は先頭のレイアウト、`?dpi=` で 72–600(既定300)
- レイアウト操作は新設 `_MainThreadInvoker` で GUI スレッドへキューイング
  して実行(HTTPワーカースレッドからの直接呼出しを回避)、PDF出力は
  `_layout_lock` で直列化。一時PDFは送信前に削除
- SPEC.md / SPEC_JP.md のエンドポイント一覧を更新

## [4.0.4] - 2026-10-28 サイトスキャン指摘対応

- `kasugai_export._export_qml_assets()` の .qml パースを stdlib
  `xml.etree.ElementTree` から vendored `defusedxml.ElementTree` へ切替
  (B405/B314 指摘をコード側で解消。geo_import と同じく ElementTree
  facade のみ同梱: `__init__.py`/`common.py`/`ElementTree.py`/`LICENSE`)
- 配布ZIPダウンロード `_download()` に https スキーム検証を追加し、
  `kasugai_download_url()` も https のみ採用へ(B310 指摘に対し
  # nosec の位置を修正した上で実コードでも http を拒否)
- `server_manager.py`(カーソル追跡イベントフィルタ)と
  `settings_dialog.py`(レジストリ自動検出)の try/except/pass に
  # nosec B110 と理由コメントを明示
- `.bandit` に `exclude = defusedxml` と B405 スキップを追加、
  `.flake8` に `defusedxml/*.py` の per-file-ignores を追加

## [4.0.3] - 2026-10-27 配布前チェックの lint findings 0 化

- flake8(プラグイン同梱 `.flake8` 設定)で残っていた 4 findings を解消:
  - `plugin.py` の未使用 import `from qgis.core import Qgis` を除去(F401)
  - `panel.py` のツールチップ翻訳呼出し2件の継続行インデントを修正(E128)
  - `kasugai_export.py` の過剰な空行を整理(E303)
- 機能変更なし(配布 ZIP 作成前の plugins.qgis.org スキャン相当
  チェック通過のための整理)

## [4.0.2] - 2026-10-27 生成HTMLのロケール対応とカタログ整理

- エクスポート起動HTML(`index.html`・`<engine>.html`)を
  日本語ベタ書き(`lang="ja"`固定)から英語ソース＋`__T_*__`
  トークン方式へ改修。`kasugai_export._localize_page()` が
  `i18n_json.translate_text()` で `geo_webview.page` コンテキストを
  引き、QGISのUI言語に追従した起動HTMLを出力する
  (未対応言語は従来通り英語)。JS内メッセージも同一仕組みで置換
- `/present` 共有ページの表示文字列(操作ヒント・ナビボタン
  title/tooltip・HUDラベル・独立ビュー表示)を同じ仕組みで
  ローカライズ(`server_manager._localize_page()`)
- `i18n/*.json` 9言語へ `geo_webview.page` コンテキスト41キーを追加
- ソースから参照されなくなった旧文言のカタログキー39件を除去
  (旧「▶ Open」・`+ kasugai_canvas.zip` 時代のツールチップ・
  削除済み OGC/ビューア経路のメッセージ・旧インストール通知等)
- なお `panel.py` のエンジンコンボ再構成(`addItem("Cesium (3D)")` 等)
  と `ZIP`/`📁` ボタンラベルは tr() 未マークのまま(固有名詞のため
  実害なし)

## [4.0.1] - 2026-10-27 KASUGAI 出力 UI の未翻訳文字列を9言語カタログへ追記

- `i18n_tool.py check` で検出されたカタログ未登録26キー
  (実行時は全言語で英語フォールバックしていた)を
  `i18n/*.json` 9言語全てへ追記:
  - `geo_webview` コンテキスト 19件:
    「▶ Canvas」「▶ WebView」ボタン、Export/ZIP/📁/↺/? の
    ツールチップ、保存先選択ダイアログと成否メッセージ、
    起動フォールバック通知(`Exported to {0}. {1}` /
    `KASUGAI Canvas is not running…` / `Local delivery…` /
    `Serverless delivery…` / `No engine available…`)等
  - `QMapPermalinkPanelBase` コンテキスト 7件
    (panel_base.ui 側の同一文字列)
- 翻訳は ja/de/es/fr/it/pt/ru/zh/hi を作成。`{0}`/`{1}`/
  `<channel>` 等のプレースホルダと製品名は保持
- なお `kasugai_export.py` の起動HTMLテンプレート
  (`_ENGINE_LAUNCHER_HTML`/`_LAUNCHER_INDEX_HTML`)は
  `lang="ja"` 固定の日本語ベタ書きのまま残存(生成HTMLの
  `translate_text` 化は別途対応が必要)

## [4.0.0] - 2026-10-27 マルチエンジンを主軸としたメジャー更新

主な変更: **マルチエンジン**（Cesium / MapLibre / OpenLayers / Leaflet）
対応を本プラグインの主軸として確立し、配信アーキテクチャと
ドキュメントをこれを中心に全面再構成した。

- マルチエンジン配信アーキテクチャの確立:
  - 同じ `.kasc`+`DATA/` を4エンジンで再生（`?engine=` / `<engine>.html`）
  - エンジン本体は GitHubPages CDN（kasugai-canvas-web、
    `stable`/`unstable` チャンネル）から配信し、
    データのみ自ホスト/WebGIS から供給する構成を既定化
  - 起動HTMLはローカル探索（`./ ../ ../../ /`）→ ホスト版への
    フォールバックで CDN/同梱の混在にも対応
- パネルを3行構成に整理（保存行/CDN行/起動行）し、
  【エクスポート】【ZIP】【▶ WebView】【▶ Canvas】を機能の柱として明確化
- 専用ドキュメントサイトを新設: `docs/`（index + architecture /
  features / engines / getting-started / technical / license）。
  正式ドキュメントは本サイトとし、`DOC_JP.md` を生成元として
  `scripts/build_geo_webview_docs.py` で自動生成
  （左サイドバー目次・Mermaid 構成図・3本柱カード）。
  README は最小構成（概要＋リンク＋クイックスタート）へ縮小
- 配布 ZIP から `docs/` を除外（build-plugin-zip.py の除外強化）
- パネル「Web配信」グループの枠上（右上）に `?` ヘルプボタンを追加:
  ドキュメントサイト（GitHub Pages）をブラウザで開く

## [3.37.0] - 2026-10-27 ZIP をダウンロード方式へ変更（エクスポート時生成を廃止）

- パネル【エクスポート】で `kasugai_canvas.zip` を生成しなくなった
  （`.kasc`+`DATA/`+`<engine>.html`+`index.html` のみ出力。
  bridge `kasugaiExport(emit_zip=True)` は従来通りZIP生成可）
- パネルに【ZIP】ボタンを追加（CDN 行に配置）: エクスポート物一式を
  `kasugai_canvas_<チャンネル>.zip` としてブラウザでダウンロードする
  （ファイル名は CDN コンボのチャンネルを反映。例 stable →
  `kasugai_canvas_stable.zip`、カスタムURLは末尾パス要素）
- `/export-data/kasugai_canvas*.zip` はファイル未生成でも
  オンデマンドで ZIP を固めて返すようにした
  （`Content-Disposition: attachment` 付き。常に直近エクスポートの最新内容。
  エクスポート実行時は残存した旧ZIPを除去して陳腐化を防止）
- 出力される `index.html` に「パッケージ ZIP」セクションを追加
  （サーバレス WEB 配信経路の下。HTTP 配信時のみ有効）
- README/README_JP: 連携構成図を最終形に整理
  （外部HTTPサーバー→WebGIS 改名、ZIP ダウンロード→静的ホスト/Re:Earth
  の2系統配線、CDN→WebGIS 配線追加、サブグラフ順序整理、
  ArcGIS ノード簡素化）＋ セクション4「WebGIS」に
  外部ホスト配信の2パターン（CDN 利用/同一ホスト同梱）比較を追記
