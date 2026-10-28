# 変更履歴(Changelog)

このファイルでは geo_webview プラグインの主な変更点を記録します。

記法は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に基づき、
[Semantic Versioning](https://semver.org/spec/v2.0.0.html) に準拠します。

## バージョン形式: VA.B.C

- **A**: QGIS コア更新やプラグインアーキテクチャ大幅変更などのメジャー変更
- **B**: UI 変更・新機能追加・中規模な機能拡張
- **C**: 軽微な不具合修正・小改善・プロファイル/プラグインの微修正

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
