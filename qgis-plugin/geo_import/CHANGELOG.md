2.8.0 翻訳方式を `i18n/<lang>.json` に移行 + レイヤ整理連携
- `.ts`/`.qm`・`.pro`・`generate_qm.py`・`update_translations.py`・
  `TRANSLATION.md`・`scripts/*-strings.sh`・i18n補助スクリプト群を廃止。
  `{"context": {"英語ソース": "翻訳"}}` のJSONカタログを新設し、
  `i18n_json.py`(全プラグイン共通ローダ)の `install_translator()` で
  起動時ロードに集約(CKANBrowser_*.qmレガシー探索とenフォールバックの
  二重installを廃止)。言語セットを共通9言語(de/es/fr/hi/it/ja/pt/ru/zh)に
  統一し en/fi カタログを廃止。
- `GeoImport` contextの未登録5メッセージ(SQLiteキャッシュ等)を全9言語で補完。
- レイヤ整理連携: `load_resource_clicked` で追加したレイヤを
  `layersAdded` で収集し、`qgis_live_driver` の `layer_org` サービス
  (プロファイルのルールでグループ配置・リネーム・スタイル適用)へ渡す。
  ドライバ未ロード・プロファイル無効時は従来どおりプロジェクト直下に
  flat追加。bridge `loadSelected` の応答に `organized` レポートを同梱。

2.7.0 カタログ取得のデフォルトをネットワーク直接参照に変更
- これまで検索・一覧はローカルSQLiteキャッシュ(Refresh SQLiteでの一括ダウンロード)
  を前提としていたが、デフォルトをCKAN APIへの直接問い合わせ(ネットワークモード)
  に変更。サイト切替時・検索時に一括ダウンロードを行わない。
- ローカルダウンロード(SQLiteキャッシュ)はオプション化:
  - メイン画面の「Use local download for this site」チェックでサイト単位に選択可
    (`ckan_servers.json` の `local_cache_sites` にURL単位で保持)。
    ON時は既存キャッシュがあればそれを利用し、無ければ一括ダウンロードを実行。
    「Refresh SQLite」ボタン押下でもそのサイトのローカル利用が自動ONになる。
  - 設定ダイアログの「Use local download for all sites」で全サイト一括指定可
    (サイト個別設定より優先。QSettings `geo_import/use_local_cache_all`)。
- ネットワークモードではカテゴリ一覧を `group_list` APIから取得し、
  `package_search` の `fq=groups:` フィルタを実装してカテゴリ絞り込みに対応。
- データプロバイダ画面のサーバー一覧でローカル利用サイトに `[local]` マーカー表示。
- bridge `status()` に `use_local_cache_all` / `local_cache_sites` /
  `current_site_local_cache` を追加。
- ローカルフォルダ型サーバー(LOCAL type/local://file://)は従来通り常にローカル扱い。

2.6.0 国際化(i18n)対応
- UI・ログ文字列を英語ソースに統一し、翻訳コンテキストを `GeoImport` に正規化
  (`Util`/`self.util` 等の不一致コンテキストを解消しカタログが実行時に適用されるようにした)。
- 表示用文字列「すべて」(formatフィルタ)を `translate('GeoImport', 'All')` に統一し、
  比較ロジックと表示を一致させた。
- `i18n` カタログを再生成し日本語113メッセージ全訳、`geo_import_ja.qm` を再コンパイル。
  他言語(de/en/es/fi/fr/hi/it/pt/ru/zh)は既存訳を継承・英語フォールバック。
- XML属性テーブルローダ・CSV診断等のユーザー向けメッセージを翻訳対象化。

2.5.0 QGIS4以降への対応宣言
- `metadata.txt` の `qgisMinimumVersion` を 3.40 → 4.0 に更新
  (QGIS4以降専用。`qgisMaximumVersion=4.99`・`supportsQt6`は継続)
- バージョン表記をV接頭辞なしに統一(V2.5.0 → 2.5.0。CHANGELOG旧エントリ・metadata内changelogのV接頭辞も全除去)
- 残存していたQt5向けフォールバック・非スコープenumを除去しQt6専用コードに統一
  (`update_translations.py` は pylupdate6 専用に更新)

2.4.0 QGIS Live Harness: AI/外部制御ブリッジ追加
- `bridge.py`(`GeoImportBridge`)を新設し `plugin.bridge` に配線。
  `qgis_live_driver` の `bridge_call`(ファイルJSONL / REST /api/cmd /
  MCP `qgis_bridge_call` / AIアシスタントパネル)と `describe_plugins`
  カタログから利用可能。メソッド(JSON文字列返却):
  `pluginInfo` / `status` / `openDialog` / `closeDialog` / `openSettings` /
  `search` / `results` / `selectResult` / `resources` / `checkResources` /
  `loadSelected`
- `openDialog` は plugin.run() の `dlg.exec()` とは別に非modalの
  `show()` で開く(呼出が即応答するため)。`search` のデータセット取得は
  内部QThreadで非同期のため `results()` で結果を取得する。
  `loadSelected` 中の警告系modal QMessageBoxは自動Ok応答に差し替え、
  メッセージを収集して返す
- 機能変更なし(UI操作は従来通り)

2.3.46 QGIS Live Harness への組み込み
- `qgis-plugin/geo_import` として管理し、upstreamリポジトリ `C:\devin\geo_import\geo_import` はHarness側フォルダへのjunctionとして同期
- プラグイン内文書を整備（README.md / CHANGELOG.md / INSTALL_INSTRUCTIONS.md / TRANSLATION.md / future-plan.md を同梱）
- 機能変更なし

2.3.0 ローカルフォルダのJSONキャッシュ処理を改善
- ローカルフォルダ利用時、packages.json/groups.jsonの生成・読み込みをキャッシュディレクトリで一元管理
- フォルダ内にJSONを残さず、SQLiteキャッシュと同じ場所に保存・参照する方式に変更
- 既存のローカルJSONも初回のみキャッシュにコピーし、以降はキャッシュ優先で動作

2.2.0 XMLファイル属性テーブル読み込み機能を追加  
- XMLファイルを属性テーブル（ジオメトリなし）として読み込み可能
- 複数XMLファイルのタイプ別自動マージ機能
- 国土交通省XML形式の自動検出と最適化処理
- DTD、名前空間、ルート要素による高精度なXMLタイプ識別
- エンコーディング問題の自動解決（Shift_JIS、UTF-8等に対応）
- CSV等と同様の統合データロード機能

2.1.0 ローカルフォルダスキャン機能を拡張  
- 拡張子制限を撤廃し、除外対象以外のすべてのファイルをデータベース化  
- システムファイル・一時ファイル・実行ファイルのみを除外する包括的アプローチに変更  
- 将来の新しいファイル形式に自動対応

2.0.0 ロカールフォルダに対応  
1.4.8 ダウンロード先のフォルダ名を人間でも分かりやすく修正  
1.4.0 CKAN以外のサーバー対応へ移行準備（サーバー一覧へサーバー種類を追加）   
1.3.0 全選択対応  
1.2.0 WMS対応  
1.1.0 XYZ対応  
1.0.0 QGIS用データカタログ統合プラグイン yamamoto版 初版公開  
- ローカルSQLiteキャッシュ検索時もカテゴリ（グループ）フィルタが有効
- CSVファイルの区切り文字自動判定（カンマ・セミコロン・タブ・コロン・スペース対応）
- CSVファイルの文字コード自動判定（UTF-8/CP932）とQGISレイヤ追加時のencoding自動指定
- CSVに緯度経度カラムがあれば自動でポイントジオメトリ化
- UIの一部改善

