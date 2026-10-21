
# QGISデータカタログ統合 将来計画 / QGIS Data Catalog Integration: Future Plan

このドキュメントは、QGISと多様なデータカタログの統合に関する将来の理想像・計画・アイデアを具体的にまとめたものです。現状の実装や進捗ではなく、「こうなってほしい」「こうしたい」という未来志向の内容です。

This document outlines the future vision, plans, and ideas for integrating QGIS with various data catalogs. It is forward-looking and describes what we want to achieve, not the current implementation or progress.


## 概要 / Overview


QGISから多様なデータカタログ（CKAN, DKAN, DataHub, Socrata, OpenDataSoft, GeoNetwork, Dataverse, Metacat, Piveau, SMB共有など）を横断的に検索・参照し、地理空間データやオープンデータセットをQGISプロジェクトへシームレスに統合できる世界を目指します。

We aim to create an environment where users can seamlessly search and access a wide variety of data catalogs (CKAN, DKAN, DataHub, Socrata, OpenDataSoft, GeoNetwork, Dataverse, Metacat, Piveau, SMB shares, etc.) from QGIS, and integrate geospatial and open datasets directly into QGIS projects.


将来的には、データの発見・取得・活用・管理までを一気通貫でサポートし、GIS分析の生産性とデータ活用の幅を大きく広げることが目標です。

Ultimately, the goal is to support the entire workflow from data discovery and acquisition to utilization and management, greatly enhancing the productivity of GIS analysis and the breadth of data use.


## 目指す方向性 / Future Directions


### 1. 多様なデータカタログの統合 / Integration of Various Data Catalogs

- 主要なオープンデータカタログ（CKAN, DKAN, DataHub, Socrata, OpenDataSoft等）や地理空間メタデータカタログ（GeoNetwork等）、学術・研究データカタログ（Dataverse, Metacat等）、Linked Data/拡張型カタログ（Piveau等）、ローカルネットワーク共有（SMB, WebDAV等）を一つのUIから横断的に検索・利用可能にする

	Enable cross-search and use of major open data catalogs (CKAN, DKAN, DataHub, Socrata, OpenDataSoft, etc.), geospatial metadata catalogs (GeoNetwork, etc.), academic/research data catalogs (Dataverse, Metacat, etc.), Linked Data/extended catalogs (Piveau, etc.), and local network shares (SMB, WebDAV, etc.) from a single UI.

- 新しいカタログやAPI仕様にも柔軟に対応できる拡張性

	Ensure extensibility to flexibly support new catalogs and API specifications.


### 2. 横断的なデータ発見・検索 / Cross-catalog Data Discovery & Search

- キーワード、カテゴリ、地域、日付、データ種別など多様な条件でカタログ横断検索

	Enable cross-catalog search using various criteria such as keywords, categories, regions, dates, and data types.

- メタデータの標準化・マッピング（ISO19115, DCAT-AP等）による一貫した検索体験

	Provide a consistent search experience through metadata standardization and mapping (ISO19115, DCAT-AP, etc.).

- 検索結果のプレビューやメタデータ詳細表示

	Support previewing search results and displaying detailed metadata.


### 3. QGISへのシームレスなデータ統合 / Seamless Data Integration into QGIS

- 検索結果からワンクリックでQGISレイヤとして追加・インポート

	Allow one-click addition/import of search results as QGIS layers.

- WMS/WFS/ダウンロードリンク等の自動判別と最適なレイヤ追加

	Automatically detect WMS/WFS/download links and add the optimal layer.

- 必要に応じてデータ変換・形式統一も自動化

	Automate data conversion and format unification as needed.


### 4. ユーザー体験の向上 / Improved User Experience

- QGISブラウザパネルや独自パネルでの直感的な操作UI

	Provide an intuitive UI via the QGIS browser panel or a custom panel.

- カタログの追加・設定をGUIで簡単に

	Enable easy addition and configuration of catalogs via GUI.

- 検索条件や履歴の保存、お気に入り管理、タグ付け

	Support saving search conditions/history, managing favorites, and tagging.

- ユーザー認証やアクセス制御の統合（社内カタログ等）

	Integrate user authentication and access control (for internal catalogs, etc.).


### 5. オープンで拡張可能な設計 / Open and Extensible Design

- Python/QGIS Pluginとしての開発・配布

	Develop and distribute as a Python/QGIS plugin.

- API駆動型で新しいカタログやプロトコルにも柔軟対応

	Adopt an API-driven approach for flexible support of new catalogs and protocols.

- オープンソースでの運用と外部貢献の受け入れ

	Operate as open source and welcome external contributions.



## 想定ユースケース（将来） / Future Use Cases

- オープンデータカタログから最新の地図や統計データを素早く探索しQGISで活用

	Quickly find and use the latest maps and statistical data from open data catalogs in QGIS.

- 地理空間メタデータカタログ（GeoNetwork等）から空間データを検索し地図作成・分析

	Search for spatial data from geospatial metadata catalogs (e.g., GeoNetwork) for map creation and analysis.

- 社内の研究データカタログや共有フォルダから必要なデータを素早く発見

	Quickly discover necessary data from internal research data catalogs or shared folders.

- 複数カタログを横断してデータの所在や公開状況をチェック

	Check the location and publication status of data across multiple catalogs.

- 分析プロジェクトごとに必要なデータソースを一元管理

	Centrally manage required data sources for each analysis project.

- 検索履歴やお気に入り機能で再利用性向上

	Improve reusability with search history and favorites features.

- データセットのバージョン管理や更新通知

	Manage dataset versions and receive update notifications.

- 他GISソフトや外部アプリとの連携拡張

	Expand integration with other GIS software and external applications.



## 今後の展望・課題 / Future Prospects & Challenges

- より多くのカタログAPI（REST, OGC CSW, DCAT, etc.）への対応

	Support for more catalog APIs (REST, OGC CSW, DCAT, etc.)

- 認証が必要なカタログ（社内リポジトリ等）への対応

	Support for catalogs requiring authentication (e.g., internal repositories)

- メタデータ標準（ISO19115, DCAT-AP等）とのマッピング強化

	Enhanced mapping to metadata standards (ISO19115, DCAT-AP, etc.)

- データセットの品質チェックや利用レポートの自動化

	Automation of dataset quality checks and usage reports

- コミュニティとの連携による拡張プラグインの開発

	Development of extension plugins in collaboration with the community

- QGISプラグインとしての配布方法検討

	Consideration of distribution methods as a QGIS plugin

- ユーザー体験向上のためのUI/UX設計

	UI/UX design for improved user experience



## 貢献方法（将来） / How to Contribute (Future)

本プロジェクトはオープンソースとして開発・運用され、将来的には以下のような貢献を歓迎します。

This project is developed and operated as open source, and in the future, we welcome the following contributions:

- バグ報告、機能提案、コード/ドキュメントのコントリビュート

	Bug reports, feature suggestions, code/documentation contributions

- 新しいカタログ対応やUI/UX改善の提案

	Proposals for new catalog support or UI/UX improvements

- 利用事例やユースケースの共有

	Sharing use cases and examples



## ライセンス / License

MIT License（または適切なOSSライセンスを明記予定）

MIT License (or another appropriate OSS license to be specified)


---

> ※このファイルは将来の構想・計画を記載するためのものです。現状の進捗や実装内容は含まれていません。

> This file describes future plans and ideas. It does not include current progress or implementation details.

