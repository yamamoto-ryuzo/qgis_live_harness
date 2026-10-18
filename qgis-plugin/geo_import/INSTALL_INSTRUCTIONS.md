# QGISプラグイン インストール手順（QT6対応版）

## 修正内容

### 1. metadata.txtの修正
- ❌ 削除: `required_qt_version=6` （存在しないフィールド）
- ✅ 設定: `qgisMinimumVersion=3.40` （QT6をサポート）
- ✅ 設定: `qgisMaximumVersion=3.99`

### 2. geo_import_main.py（geo_import メインファイル）の修正
- ロケール取得時のエラー処理を追加（Noneチェック）
- 重複したコードブロックを削除（Settings初期化が2回行われていた問題を修正）
- QT5/QT6互換のためqgis.PyQtを使用

### 3. 全Pythonファイルの更新
- PyQt5インポートをqgis.PyQtに変更してQT5/QT6自動互換に対応

## インストール方法

### 方法1: ZIPファイルからインストール

1. プラグインZIPファイルを作成（既に作成済み）:
   ```
   QGISDataCatalogIntegration_2.3.13.zip
   ```

2. QGISを起動

3. メニューから: プラグイン → プラグインの管理とインストール

4. 「ZIPからインストール」タブを選択

5. `QGISDataCatalogIntegration_2.3.13.zip` を選択してインストール

### 方法2: 手動インストール

1. QGISのプラグインフォルダを開く:
   - Windows: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
   - Mac: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
   - Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`

2. `qgis_data_catalog_integration` フォルダをコピー

3. QGISを再起動

## 動作確認

1. QGISメニュー: プラグイン → プラグインの管理とインストール
2. 「geo_import」または「Catalog Integration」が表示されることを確認
3. プラグインを有効化
4. ツールバーにアイコンが表示されることを確認
5. アイコンをクリックして動作することを確認

## トラブルシューティング

### プラグインが表示されない場合

1. QGISのログを確認:
   - メニュー: 表示 → パネル → ログメッセージ
   - Pythonのエラーメッセージを確認

2. Python環境を確認:
   - QGISが使用しているPythonバージョンを確認
   - 必要なパッケージがインストールされているか確認

3. プラグインフォルダを確認:
   - `qgis_data_catalog_integration` フォルダが正しい場所にあるか
   - `__init__.py` と `metadata.txt` が存在するか

### QT6関連のエラーが出る場合

- QGIS 3.40以降を使用していることを確認
- qgis.PyQtは自動的にQT5/QT6を切り替えるため、追加設定は不要

## 技術仕様

- **対応QGISバージョン**: 3.40 - 3.99
- **QT互換性**: QT5/QT6自動対応（qgis.PyQt使用）
- **標準言語**: 英語（UI）
- **コメント**: 日本語（コード内動作説明）
- **UI方式**: Qt Designer .uiファイル
