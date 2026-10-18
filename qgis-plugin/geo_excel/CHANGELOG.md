# CHANGELOG — geo_excel

## 1.3.0

- `metadata.txt` の `qgisMinimumVersion` を 3.40 → 4.0 に更新
  (QGIS4以降専用。`qgisMaximumVersion=4.99`・`supportsQt6`は継続)
- bridge の自動応答を Qt6 の `QMessageBox.StandardButton` スコープenumに修正

## 1.2.0

- **AI/外部制御用ブリッジ**(`bridge.py` の `GeoExcelBridge`)を追加し
  `plugin.bridge` に配線。`qgis_live_driver` の `bridge_call`
  (ファイルJSONL / REST /api/cmd / MCP `qgis_bridge_call` /
  AIアシスタントパネル)と `describe_plugins` カタログから利用可能。
  メソッド(JSON文字列返却):
  - `pluginInfo()` / `status()` / `listScripts()`
  - `layerVariables(layer_id)` / `setLayerVariables(vars, layer_id)`
    — 帳票出力に必要なレイヤ変数 `xlsout_*`・`dpi` の取得/設定
  - `run(script, feature_id, confirm)` — 帳票実行。scriptは
    list|single|bulk|ファイル名|index。スクリプト内のmodal
    QMessageBox(上書き/続行確認・完了通知)は実行中だけ自動応答に
    差し替え、confirm=False(既定)では確認系をCancel=中断として扱う
    安全側の既定。messageBar().pushCritical の呼出も収集して返す。
    Excel起動・生成中はGUIスレッドをブロックする(メニュー実行と同じ)
- `plugin.py` の `_exec_script` がexec名前空間を返すように拡張
  (スクリプト側の `excel_result`/`output_path` をbridgeが取得するため)

## 1.1.0

- プラグインID・フォルダ名を `export_excel` から `geo_excel` に改名
  (他プラグインと命名規則を統一)。deploy先ディレクトリ・メニュー名・
  upstream gitdir(`.upstream/QGIS-exportExcel.git`)の core.worktree も追従。
  upstreamリポジトリ名(QGIS-exportExcel)自体は変更なし

## 1.0.0

- QGIS-exportExcel (https://github.com/yamamoto-ryuzo/QGIS-exportExcel) の
  レイヤアクション用スクリプト群(exportList/exportSingle/exportSingleBulk)を
  無改変で同梱し、プラグインメニューから実行できる簡易ラッパーとして組み込み。
  - `[% @layer_id %]` はアクティブなベクターレイヤ、`[% $id %]` は選択地物で
    実行時に置換する
  - スクリプト内の `PyQt5` 固定importは exec 直前にソースを `qgis.PyQt` へ
    書き換えて吸収(Qt6対応。QGIS4のimportフックがPyQt5を禁止するため
    sys.modules shim は不可)。`Qt.WaitCursor` も `Qt.CursorShape.WaitCursor`
    へ同時に書き換える(Qt6のスコープenum対応)
- 実行には win32com(pywin32) と Excel が必要(upstreamと同じ前提)
