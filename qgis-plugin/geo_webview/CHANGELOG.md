# 変更履歴(Changelog)

このファイルでは geo_webview プラグインの主な変更点を記録します。

記法は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に基づき、
[Semantic Versioning](https://semver.org/spec/v2.0.0.html) に準拠します。

## バージョン形式: VA.B.C

- **A**: QGIS コア更新やプラグインアーキテクチャ大幅変更などのメジャー変更
- **B**: UI 変更・新機能追加・中規模な機能拡張
- **C**: 軽微な不具合修正・小改善・プロファイル/プラグインの微修正

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
