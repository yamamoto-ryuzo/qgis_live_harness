# geo_webview — 仕様書

この仕様書は `README.md` と `CHANGELOG.md` の内容に基づき、機能別に整理した正式な仕様を提供します。
対象リポジトリ: `geo_webview`（ルートに配置）。

## 目的と範囲
- 目的: geo_webview プラグインの機能を明確に仕様化し、実装・運用・テストの基準を定める。
- 範囲: サーバレス Web 配信（`.kasc`+`DATA/` エクスポート＝**主機能**）、組み込みHTTPサーバー（`/kasugai`・`/export-data/`・`/present`・`/screenshot`・パーマリンク受領＝補助）、パーマリンク生成・ナビゲート、テーマ適用、External Control の挙動、投影（CRS）ポリシー、セキュリティ/運用上の注意。

## 1. 機能概要
- **サーバレス Web 配信（主機能）**: 開いている QGIS プロジェクトを `.kasc`+`DATA/` パッケージとして出力し、KASUGAI Canvas のマルチエンジン（Cesium/MapLibre/OpenLayers/Leaflet）で再生する。出力物＋エンジンを静的ホストへ置くだけで配信できる。起動経路はパネル（`Export`=ファイル出力のみ / `▶ Open`=登録・起動まで）・`GET /kasugai`・bridge `kasugaiExport` の3系統で、Canvas登録→本サーバ静的配信→ホスト版エンジンの3段フォールバックを持つ（§15）。
- 組み込み HTTP サーバー（補助）: `/kasugai` `/export-data/` `/present` `/present/state` `/screenshot` `/received` を提供（v3.29.0 で OGC サービスは廃止）。
- パーマリンク生成: QGIS の現在表示（中心座標、scale、rotation、theme など）を HTTP パーマリンク（`/qgis-map` パス）として生成・コピー・開く。`/qgis-map` は HTML を返さず、受領記録・External Control ナビゲートの URL パスとして使う（v3.24.0 でプラグイン内蔵ビューアは廃止）。
- Theme サポート: `theme` パラメータのマップテーマをナビゲーション時に適用し、`.kasc` へ `theme:` 行として出力（プロジェクト自体は変更しない）。
- External Control: 外部からの `/qgis-map` や `/wms` を含むリクエストを受け、許可された場合に自動で QGIS をナビゲートする。
- レンダリング: `/screenshot` は現在のキャンバス MapSettings（回転含む）を `QgsMapRendererParallelJob` で複製描画し PNG を返す（`w`/`h` 指定・4096px クランプ・`_render_lock` 直列化・30秒タイムアウト）。

---
## 2. API / エンドポイント仕様（高水準）
- GET `/kasugai` — `.kasc`+`DATA/` エクスポート＋Canvas 登録。`engine=`（cesium|maplibre|openlayers|leaflet、既定 cesium）・`install=1`（未検出時に配布ZIP取得）を受け付ける。応答 JSON `{ok,url,via,dir,layers,tiles,engine}`。
- GET `/export-data/<rel>` — 直近エクスポート出力先配下のファイル配信（.kasc/DATA/・起動HTML等）。
- GET `/<engine>/...` — インストール済み KASUGAI Canvas の `web/` を静的配信（エンドポイント不一致パスのフォールバック解決）。
- GET `/present` `/present/state` `/screenshot` — 画面共有ページ・キャンバス状態 JSON・キャンバス PNG。
- GET `/received` — 受領パーマリンク履歴 HTML。
- GET `/qgis-map` — パーマリンク URL のパス。HTML は返さず、受領記録・External Control のナビゲートトリガとして使う。
- HEAD `/export-data/`・`/<engine>/` — ランチャー HTML のエンジン自動探索プローブ用（静的配信のみ応答）。
- OPTIONS — CORS+Private Network Access プリフライト（hosted エンジン https→localhost の fetch 用）。

共通的な振る舞い:
- サーバはデフォルトでポート範囲 8089-8099 を試行してバインドする。
- 外部アクセスを許可する場合はホストを 0.0.0.0 にバインドするが、運用ではファイアウォールで制限推奨。

---
## 3. パーマリンク形式とパラメータ
基本（推奨）
- `x` : 経度（または投影座標系の X）
- `y` : 緯度（または投影座標系の Y）
- `scale` : QGIS の scale（例: 1000.0）
- `crs` : 省略時は `EPSG:4326` として解釈。
- `rotation` : 表示の回転（度）
- `theme` : マップテーマ名（存在する場合に適用する）

例:
```
http://localhost:8089/qgis-map?x=139.01234&y=35.12345&scale=1000.0&rotation=0.00
```

短縮形式（プレゼン資料向け）
- 小数切り捨て等で `x=139&y=35&scale=1000.0` のように短くできる。

変換ルール:
- `scale` 指定があれば優先して適用。
- `zoom` は内部推定（Web マップ用の推定）で用いるが、基本は `scale` を優先。

---
## 4. Web 配信（KASUGAI Canvas エクスポート）

プラグイン内蔵の生成HTMLビューア（旧 `/qgis-map`・`/maplibre`・`/map3d`）は
**v3.24.0 で廃止**され、閲覧は KASUGAI Canvas に一本化された。
現在の Web 配信は `.kasc`+`DATA/` エクスポートが中核であり、詳細は §15 を参照。

- 生成物: `kasugai_canvas.kasc`・`index.html`・`<engine>.html`×4（cesium/maplibre/openlayers/leaflet）・`project.json`・`bookmarks.xml`・`DATA/`（GeoJSON/ネイティブ形式/.qml/タイル複製）。
- 起動 HTML: `?kasc=<.kasc URL>` 付きで対応エンジンへ転送し、エンジン本体を `./ ../ ../../ /` の順に自動探索（`CANVAS_BASE` で差し替え可。エンジン未検出時は `HOSTED_BASE` のホスト版エンジンへ誘導）。

---
## 5–9. OGC サービス（v3.29.0 で廃止）

WMS / WMTS・XYZ / WFS・`/maplibre-style` の各エンドポイントと関連内部実装
（`wms_service.py`・`wmts_service.py`・`wfs_service.py`・`sld_renderer.py`・
`maplibre/`、ANGLE パイプライン、WFS/WMTS キャッシュ）は v3.29.0 で撤去。
プラグインはサーバレス配信（`.kasc`+`DATA/` 出力＋`/export-data/` 配信）に専念する。
旧実装の詳細は git 履歴を参照。


## 10. Google Maps / Google Earth 連携（v3.30.0 で廃止）

Google Maps / Google Earth の URL 生成・パース機能
（`_build_google_maps_url`・`_build_google_earth_url`・
`_parse_google_maps_at_url`・`_parse_google_earth_url`・パネルの外部
起動ボタン・bridge の `googleMapsUrl`/`googleEarthUrl`/`openExternal`
の Google 対応）は v3.30.0 で撤去。Google Earth へのリンクは
KASUGAI Canvas 側のベースマップコントロールが担う。
旧実装の詳細は git 履歴を参照。

---
## 11. External Control（外部制御）のパース優先度と挙動
- 機能: パネルの `External Control` が有効なら、外部から受信した URL を自動適用して QGIS をナビゲートする。
- パース優先度は上記 §6 に準じる。
- 動作:
  - 受信 URL をパースして `navigate_from_http` ルートを使い QGIS の表示を更新する。
  - パネル起動時に既に受信済みの URL がある場合は自動ナビゲートを実行（設定に依存）。
- セキュリティ: 自動ナビゲートは UX を上書きするため、明確な ON/OFF トグルを持ち、ログに受信元・実行時刻を記録することを推奨。

---
## 12. テーマ (Theme) サポート
- `theme` パラメータに指定されたマップテーマをナビゲーション時に適用する。プロジェクト自体の状態を変更しない。
- `theme` 値はプロジェクト内の既存マップテーマ名のみサポート。未存在の場合は No Theme（位置のみ適用）へフォールバック。
- スタイルのエクスポートでは QGIS バージョン差に備えて `exportNamedStyle` 等の呼び出しにフォールバックを用意。

---
## 13. レンダリング（/screenshot）とパフォーマンス
契約（contract）:
- 入力: `w`/`h`（または `width`/`height`）。省略時はキャンバスサイズ、上限 4096px。
- 出力: 現在のキャンバス表示と同等の PNG（回転・縮尺・表示中レイヤを反映）。

実装:
- キャンバスの `QgsMapSettings` を複製し `QgsMapRendererParallelJob` で描画する
  （`server_manager._render_map_settings`）。GUI スレッドをブロックせず、
  HTTP ワーカースレッドから呼べる。
- 複数の `QgsMapRendererParallelJob` 同時実行は QGIS クラッシュを招くため
  `_render_lock` で直列化する。30秒でタイムアウト（ジョブを cancel）。

性能上の注意:
- 大きな出力サイズはメモリと CPU を要するため 4096px でクランプする。

---
## 14. 投影 (CRS) ポリシー
- `.kasc` エクスポートのベクターは EPSG:4326 に正規化して出力する（ネイティブ参照の GPKG/Parquet/FGB はクライアント側で処理）。
- `crs` を指定しないパーマリンクは `EPSG:4326` として解釈される。
- 座標変換は `QgsCoordinateTransform` を利用。プロジェクトによっては外部の proj 定義が必要となる場合がある。

---
## 15. KASUGAI Canvas 連携（送出）

QGIS プロジェクトのレイヤツリーを、KASUGAI Canvas のプロジェクト
（`.kasc` + `DATA/`）として書き出す機能。実体は `kasugai_export.py`。

### 起動経路

| 経路 | 呼び出し | 用途 |
|---|---|---|
| パネルボタン | `▶ Canvas` / `▶ WebView` ボタン (`plugin.py: on_kasugai_launch_clicked`) | 人手操作。パネルの `Engine:` コンボで起動エンジンを選択（QSettings `kasugai_engine` に保存）。`▶ Canvas`（route=`kasugai`）は**再エクスポートせず**既存の `.kasc` を登録・ブラウザ起動（未出力時はエクスポートを促すメッセージ）。`▶ WebView`（route=`hosted`）は bridge `kasugaiExport(open_app=True)` と同じく出力→フォールバック→ブラウザ起動まで行う |
| パネルボタン | `Export` ボタン (`plugin.py: on_kasugai_export_clicked`) | 人手操作（ファイル出力のみ。Canvas 起動・登録はしない） |
| HTTP | `GET http://localhost:8089/kasugai` (server_manager._handle_kasugai) | 外部アプリ・AI からの一発起動。`?engine=` で起動エンジン指定可。応答は `{ok,url,via,dir,layers,tiles,engine}` JSON |
| Bridge | `bridge_call` の `kasugaiExport(output_dir, open_app, native_formats, hidden_as_off, embed_gpkg_style, emit_themes, emit_bookmarks, emit_launchers, engine, install, route, use_existing)` | Live Driver 経由の AI 制御（MCP `qgis_bridge_call` / REST `/api/cmd` / JSONL）。`use_existing=True` で再エクスポートせず既存の `.kasc` のみ使用（未出力なら `code=not_exported`） |

### 出力フォルダ構成

```
<out_dir>/                    # 既定: <ドキュメント>/kasugai_canvas_qgis
├─ kasugai_canvas.kasc        # インスペクタ設定(外部プロジェクト登録対象)
├─ project.json               # {"title": ...}
└─ DATA/
   ├─ *.geojson               # 変換が必要だったベクター(EPSG:4326)
   ├─ *.gpkg                  # ネイティブ参照の GPKG(複製)
   ├─ *.parquet / *.fgb       # ネイティブ参照の Parquet/FGB(複製)
   ├─ *.csv / *.tsv           # duckdb: 参照の区切りテキスト(複製)
   ├─ <dir>/                  # ローカル 3D Tiles / ローカル XYZ タイルの複製(1GiB 上限)
   └─ *.qml                   # 各ベクターレイヤの QGIS スタイル
```

### .kasc 行の生成規則

| QGIS 側 | .kasc 行 | 備考 |
|---|---|---|
| GPKG ソース(地理座標系) | `gpkg: グループ/名 | DATA/x.gpkg | on | table=<表> | style=DATA/x.qml` | ファイルを DATA/ へ複製。複数テーブルは1ファイルを共有 |
| GeoJSON/Parquet/FGB ソース | `geojson:` / `geoparquet:` / `flatgeobuf:` 参照行 | ローカルは複製、http(s) は URL をそのまま記述 |
| CSV/TSV(delimitedtext・ogr) | `duckdb: 名 | DATA/x.csv | on | format=csv | lon=<列> | lat=<列>` | ジオメトリ列は `geom=`。delimitedtext は URI の xField/yField/wktField を引き継ぎ、ogr CSV はヘッダから推定。delimitedtext で非地理座標系の場合は GeoJSON 変換 |
| フィルタ(subsetString)付き GPKG | `gpkg: … | where=<フィルタ>` | ネイティブ参照のままフィルタ維持 |
| フィルタ付き Parquet | `duckdb: 名 | DATA/x.parquet | on | format=parquet | where=<フィルタ>` | `geoparquet:` には where= が無いため duckdb: に切替 |
| フィルタ付き GeoJSON/FGB | GeoJSON(EPSG:4326)へ変換して `geojson:` 行 | フィルタを地物に反映して出力 |
| 3D Tiles レイヤ(QgsTiledSceneLayer) | `3dtiles: グループ/名 | <tileset.json URL or DATA/x/tileset.json> | on` | http(s) は URL 参照、ローカルはディレクトリごと DATA/ へ複製(1GiB 上限・超過は skipped) |
| XYZ タイルラスタ | `xyz:` 行。表示中の**最下段**のみ `base:` 行（既定ベースマップとして既定群の先頭に置く）。「背景図」「ベースマップ」「basemap」名のグループ内にある XYZ は位置・表示状態に関わらず全て `base:` 行（ベースマップ候補）として登録し、グループ名はタイトルから外す（配下のサブグループは残し、Canvas のベースマップ選択でグループ化表示される）。非表示の候補は `| off` 付きで出力。グループ名は設定ダイアログの Basemap Groups（QSettings `kasugai_basemap_groups`・カンマ区切り）で追加可能 | zmin/zmax → minZoom=/maxZoom=。不透明度は opacity=、限定範囲は bbox=西経,南緯,東経,北緯 |
| XYZ ローカルテンプレート | `xyz:` 行(DATA/<dir>/{z}/{x}/{y}.png) | `file:///…/{z}/{x}/{y}.png` はタイルツリーごと DATA/ へ複製(1GiB 上限・超過は skipped) |
| WMS ラスタ(type=xyz 以外) | `wms: グループ/名 | <エンドポイントURL> | on | layers=, styles=, format=` | QGIS の WMS 接続 URI から url=/layers=/styles=/format= を抽出。Canvas 側が GetMap を 256px タイルへ分解して要求 |
| その他ベクター(SHP/PostGIS/WFS/メモリ等)・非地理座標系 | GeoJSON(EPSG:4326)へ変換して `geojson:` 行 | 再投影は warnings に記録 |
| 属性テーブルのみ(NoGeometry)・ローカルラスタ・ベクタータイル・メッシュ・点群・アノテーション等 | 出力せず `skipped` に種別/理由付きで記録 | |
| 非表示レイヤ | `hidden_as_off=True` 時のみ `| off` 付きで出力 | 既定(visible_only=True)では除外 |
| キャンバス | `cam:` 行(中心座標+概算高度+回転) | |
| ブックマーク | `bookmarks.xml`(qgis_bookmarks形式・EPSG:4326正規化) + `bookmark:` 行(プロジェクト+アプリケーション両方) | `emit_bookmarks=False` で抑制。Canvas 側が XML を読み込みカメラプリセットへ展開する |

その他: `attr=` に QGIS レイヤの出典(attribution)を引き継ぐ。
`embed_gpkg_style=True` なら `saveStyleToDatabase` で GPKG の
`layer_styles` にも既定スタイルを保存する(**元ファイルを更新する**)。
`sql:` 行は QGIS 側に対応する任意クエリソースが無いため出力しない
（クエリ系は `duckdb:` の宣言的オプションで網羅する）。

### KASUGAI 側への反映

起動中の KASUGAI ローカルサーバー（`KASUGAI_CANVAS_PORT`、既定 8510）が
あれば `POST /api/projects/register` で外部プロジェクト登録し、
`POST /api/command` の `switchProject` で表示を切り替える。

Canvas が使えない場合は次の順でフォールバックする
（`/kasugai`・`kasugaiExport` とも応答の `via` で供給元を返す）:

| `via` | 条件 | URL |
|---|---|---|
| `kasugai` | Canvas 稼働（or exe/関連付けで起動成功） | `http://localhost:8510/<engine>/?project=<id>` |
| `qgis-http` | Canvas 未起動だが **インストール済み** `web/` あり | `http://localhost:<port>/<engine>/?kasc=<export-data URL>` |
| `hosted` | Canvas **未インストール**（要インターネット） | `https://yamamoto-ryuzo.github.io/kasugai-canvas-web/<channel>/<engine>/?kasc=<export-data URL>` |
| `null` | いずれも不可 | 出力のみ成功 |

- `qgis-http`: geo_webview の HTTP サーバーが **エンドポイントに一致しなかった
  パスをインストール済み Canvas の `web/` 配下へ静的解決**する
  （`find_kasugai_web_dir()`）。同一オリジンのため混在コンテンツ問題なし
- `hosted`: エンジン本体は `kasugai-canvas-web`（GitHub Pages）から取得し、
  `.kasc`+`DATA/` は本サーバーの `/export-data/` から読む。https→localhost
  の fetch は Chrome Private Network Access 対象のため、サーバーは
  `OPTIONS` プリフライトに `Access-Control-Allow-Private-Network: true` で
  応答する。チャンネルは設定 `kasugai_hosted_channel`
  （`stable`/`unstable`/カスタムURL、既定 `stable`）
- エンジン起動HTML は `HEAD` メソッドで `<engine>/index.html` を自動探索する
  ため、サーバーは `HEAD`（静的配信のみ）にも応答する

### AI からの操作

- Live Driver の `qgis_bridge_call`（MCP/REST/JSONL）で
  `kasugaiExport` を呼ぶ — 推奨（引数制御可能・JSON 応答）
- または `GET /kasugai` を直接 HTTP で呼ぶ
- KASUGAI 側の WebView プラグイン `qgis-import`
  （kasugai_canvas `web/PLUGIN/`）の「QGISから取り込み」ボタンも
  同じ `/kasugai` を呼ぶ薄い実装

---
## 16. セキュリティ・運用上の注意
- デフォルトで外部アクセスを許す設計だが、公開環境ではファイアウォールやプロキシでアクセス制御を厳格に行うこと。
- `External Control` を有効にしていると任意の外部URLで QGIS の表示が書き換わるため、信頼できるネットワーク内または追加の承認フローを用いることを強く推奨。
- ログを適切に出力し、受信元IP・タイムスタンプ・実行アクションを残す運用を推奨。

---
## 17. テスト・QA 手順
自動テスト候補:
- `server_manager.py` のユニットテスト: ポート選定・バインド挙動のモックテスト。
- URL パーサ（内部形式）の単体テスト（複数フォーマットのケース）。
- `wmts` タイル座標→BBOX 変換のユニットテスト。

手動テスト手順（QGIS 実環境）:
1. QGIS を起動しプラグインをインストール。
2. `Export` で `.kasc`+`DATA/` を出力し、パネルの `Engine:` でエンジンを選び `▶ Canvas` を押してブラウザでそのエンジンが開くことを確認（未出力時はエクスポートを促すメッセージが出る）。`▶ WebView` は出力→ブラウザ起動まで一発で行う（`/kasugai` と同じフォールバックが働く）。
3. `External Control` を ON にして、別ホスト（または同一ホスト）から `/qgis-map?x=...&y=...&scale=...` にアクセスして QGIS がジャンプすることを確認。
4. `/screenshot` でキャンバス PNG が返ることを確認。
5. `/present` ページがブラウザで開くことを確認。

テスト注意:
- CI 環境では `qgis.core` や `PyQt5` が無いため、これらをモックするかローカルでの手動確認が必要。

---
## 18. 実装ファイルと責務マッピング
- `plugin.py` — メインプラグインロジック、パーマリンク/ナビゲート、パネルイベント配線。
- `panel.py` — パネル UI 実装（Web配信グループ、ナビゲート、生成、外部制御トグル等）。
- `panel_base.ui` — Qt Designer の UI 定義。
- `server_manager.py` — 組み込み HTTP サーバーの起動/停止・ルーティング（`/kasugai` `/export-data/` `/present` `/present/state` `/screenshot` `/received` `/<engine>/` 等）。
- `http_server.py` — HTTP 応答の低水準送信ユーティリティ。
- `kasugai_export.py` — KASUGAI Canvas 連携（`.kasc`+`DATA/` 生成、起動HTML生成、プロジェクト登録、コマンド送信、フォールバックURL構築）。
- `scale_zoom.py` — スケール/ズーム換算。
- `settings_dialog.py` — 設定ダイアログ（KASUGAI インストール先・ホスト版チャンネル・Basemap Groups）。
- `bridge.py` — AI/外部制御用ブリッジ（`kasugaiExport` 等）。

---
## 19. 変更履歴の要約（V2/V3 ハイライト）
- V2.0.0: WMS サポートと外部アクセス（0.0.0.0 バインド）を追加。
- V2.6.0: 投影定義と軸順情報を生成 HTML に埋め込み、座標表示の精度向上。
- V2.8.0: External Control の自動ナビゲート追加。
- V2.10.0: Google Earth `y` トークン対応とスケール推定の改善。
- V2.12.0: テーマ対応 WMS 出力（仮想マップビュー）。
- V2.13.0: WMTS タイルエンドポイント、MapLibre 改善（pitch トグル、zoom clamp 解除）。
- V3.0.0: MapLibre WFS + QGIS スタイル注入の安定化、ベーススタイルの相対URL化、ブラシ無しポリゴンの正しい境界線表示、単位正規化（mm/pt→px）を確立。

- V3.1.0: WMTS キャッシュ導入
  - サーバ側で WMTS タイルのキャッシュを有効化しました。キャッシュは各 "identity" ごとに分離され、identity は表示中のレイヤ識別子（layer ID）と各レイヤに適用されるスタイル識別子（style ID）を決定的に組み合わせた JSON を sha1 ハッシュ化し、その先頭 12 文字（short hash）を採用して生成されます。
  - GetCapabilities の ResourceURL / ServiceMetadataURL に `?v=<identity_short>` を付与することで、クライアントが現在サーバ側で有効な identity を検出できるようにしました。
  - クライアント（MapLibre）は画面移動（moveend）時に GetCapabilities を再取得し、identity が変化していれば WMTS タイルソースのみを差し替えて新しいタイルを取得する挙動を推奨します（WFS やスタイル全体の再読み込みは不要）。
  - この仕組みにより、サーバ側で表示用レイヤやスタイルが変更された際に WMTS のみを効率的に更新・無効化でき、WFS の重複登録や全スタイル再適用に起因する副作用を避けられます。
