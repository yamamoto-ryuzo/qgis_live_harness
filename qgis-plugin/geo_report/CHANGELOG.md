# Changelog - QGIS Layout Item Selector

バージョン表記: VA.B.C
- 例: V2.0.0（A=2, B=0, C=0）

## バージョン番号の意味
- **A**: QGIS本体のバージョンアップに伴う本体の修正
- **B**: UIの変更（プラグインの追加等含む）、本体の機能追加
- **C**: プロファイル・プラグイン、本体の修正

---

## 変更履歴

### V2.5.0 国際化(i18n)対応
- ハードコードされていた日本語UI文字列を英語ソースに変換し、
  `QCoreApplication.translate('geo_report', ...)` による翻訳呼出に統一。
- `i18n` カタログを再生成し日本語91メッセージ全訳、`geo_report_ja.qm` を再コンパイル。
- ログ出力も英語ソース化。

### V2.4.0 QGIS4以降への対応宣言

- `metadata.txt` の `qgisMinimumVersion` を 3.40 → 4.0 に更新
  (QGIS4以降専用。`qgisMaximumVersion=4.99`・`supportsQt6`は継続)
- 残存していたQt5向けフォールバック・非スコープenum・`exec_()`・`PyQt6`直接import分岐を除去しQt6専用コードに統一

### V2.3.0 QGIS Live Harness: AI/外部制御ブリッジ追加

- `bridge.py`(`GeoReportBridge`)を新設し `plugin.bridge` に配線。
  `qgis_live_driver` の `bridge_call`(ファイルJSONL / REST /api/cmd /
  MCP `qgis_bridge_call` / AIアシスタントパネル)と `describe_plugins`
  カタログから利用可能。メソッド(JSON文字列返却):
  `pluginInfo` / `status` / `openPanel` / `closePanel` / `listLayouts` /
  `selectLayout` / `printOptions`(scale・angle) / `showPrintArea` /
  `listItems` / `itemProperties` / `setItemProperties` /
  `saveLayoutProperties` / `loadLayoutProperties` / `openLayoutManager`
- `save/loadLayoutProperties` はファイルダイアログを通さずパス指定で
  直接JSON読み書きするため、modalで呼出をブロックしない
- 機能変更なし(UI操作は従来通り)


### V2.2.7（2026-10-18）
- QGIS Live Harness (`qgis-plugin/geo_report`) への組み込み
  - upstreamリポジトリ `C:\devin\geo_report\geo_report` はHarness側フォルダへのjunctionとして同期
- プラグイン内文書を整備（README.md / CHANGELOG.md / image.png を同梱）
- 機能変更なし

### V2.1.0（2025-07-24）
- 印刷範囲の回転角度をレイアウト本体（QgsLayoutItemMap等）に反映する機能を追加

### V2.0.0（2025-07-19）
- バージョン表記を2.0.0に更新
- 印刷範囲の回転・移動時の中心座標維持ロジックを改善
- コード整理・安定性向上

### V1.2.0
- UI改善：レイアウトリスト・レイアウト情報タブに印刷サイズ（縦横）を表示
- プロパティ編集機能の強化

### V1.1.0
- レイアウトアイテムのプロパティ保存・読込機能追加

### V1.0.0
- 初版リリース
