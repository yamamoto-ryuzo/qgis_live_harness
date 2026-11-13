# WebGIS向けデータ形式変換・レイヤ追加(KASUGAI Canvas)

QGIS 内のデータを KASUGAI Canvas(.kasc+DATA/)で最適に再生できる形式へ変換し、レイヤ追加まで行う手順。
use_when: ユーザーがデータ形式の変換・レイヤ追加・WebGIS/Canvas 向けのデータ準備・公開用データ作成を依頼したとき

## 基本方針(サーバレス優先)

- **変換サーバーを立てない**。変換は QGIS 内の processing(GDAL/ネイティブ)で完結させ、出力は「静的ホスティング+ブラウザ内デコード」できる形式を選ぶ
- KASUGAI Canvas はエンジン本体を CDN(kasugai-canvas-web)からも読めるため、**データ側も静的ファイルだけで配信できる**のが理想形
- 変換後のレイヤ追加までは `qgis_pyeval`、WebGIS への送出・起動は `qgis_bridge_call` → geo_webview `kasugaiExport` を使う

## 形式選定表

変換先は用途と規模で決める。「そのまま置いて Canvas が読める形式」を優先し、安易に GeoJSON 化しない。

| ソース/目的 | 推奨出力 | .kasc 行 | 理由 |
|---|---|---|---|
| 小〜中規模ベクター(数千地物) | GeoJSON(EPSG:4326) | `geojson:` | 最も単純。大容量では遅いので規模限定 |
| 中〜大規模ベクター(数万地物〜) | **GeoParquet(.parquet)** or FlatGeobuf(.fgb) | `geoparquet:`/`flatgeobuf:` | ブラウザ内バイナリデコードで速い・変換不要で置くだけ。GeoJSON 化は避ける |
| 大規模+条件絞込み/範囲連動 | GeoParquet + `duckdb:` | `duckdb:`(where=/bbox=auto) | 「見ている範囲だけ読む」。DuckDB-WASM 初回ロード約60MBは SW キャッシュで緩和 |
| 正データ管理・複数テーブル共有 | GeoPackage(.gpkg) | `gpkg:`+`table=` | sql.js Worker が直接読む。**地理座標系(EPSG:4326等)必須** |
| CSV/TSV(緯度経度/WKT列) | そのまま or .csv複製 | `duckdb:`+`lon=`/`lat=`/`geom=` | delimitedtext の xField/yField/wktField を継承 |
| ローカルラスタ(DEM/オルソ等) | XYZタイル か COG | `xyz:`/`geotiff:` | **エクスポートはローカルラスタを skipped する**ので事前にタイル化/COG化が必要 |
| WMSラスタ | そのまま(URL) | `wms:` | 接続URIから自動で行生成 |
| 3Dモデル/点群/建物 | 3D Tiles | `3dtiles:` | http(s)はURL参照、ローカルはDATA/へ複製(1GiB上限) |
| フィルタ(subsetString)付き | 形式ごとに維持 | `where=`(gpkg) / `duckdb:`(parquet) / GeoJSON変換(geojson/fgb) | フィルタを変質させない経路を選ぶ |
| 非地理座標系(平面直角等) | **EPSG:4326へ必ず再投影** | — | `gpkg:`ネイティブ参照もGeoJSON変換も地理座標系が前提 |

## 変換→レイヤ追加のレシピ(qgis_pyeval)

`processing.run` は GUI スレッドで同期実行。大きいデータは QGIS が一時的に固まる旨をユーザーに断る。

```python
import processing
from qgis.core import QgsVectorLayer, QgsProject, QgsCoordinateReferenceSystem

# 1) 形式変換(拡張子で出力ドライバが決まる。GeoParquetはGDAL3.5+)
processing.run("native:savefeatures", {
    "INPUT": "ソースレイヤ名またはパス",
    "OUTPUT": "C:/out/layer.parquet",   # .gpkg/.geojson/.fgb も可
})

# 2) 座標系が非地理座標系なら先に EPSG:4326 へ
processing.run("native:reprojectlayer", {
    "INPUT": "...",
    "TARGET_CRS": QgsCoordinateReferenceSystem("EPSG:4326"),
    "OUTPUT": "C:/out/layer_4326.parquet",
})

# 3) ラスタ→XYZタイル(エクスポート対象にする唯一のローカルラスタ経路)
processing.run("native:tilesxyzdirectory", {
    "EXTENT": "xmin,ymin,xmax,ymax", "ZOOM_MIN": 8, "ZOOM_MAX": 16,
    "DPI": 96, "OUTPUT_DIRECTORY": "C:/out/tiles",
})

# 4) レイヤ追加
lyr = QgsVectorLayer("C:/out/layer.parquet", "名称", "ogr")
QgsProject.instance().addMapLayer(lyr)
```

- **追加後の整理**: `qgis_bridge_call` → geo_driver `placeLayer`/`organizeLayers` で layer_org サービスの標準配置(グループ・リネーム・.qml適用)を使う。WebGIS 側のグループ/凡例構成にそのまま反映される

## 凡例・テキスト再現性の制約(Canvas 側)

Canvas の .qml コンパイラ(web/shared/qml-style.js)の対応範囲。**再現したい表現がこの範囲を外れるなら、QGIS 側で単純化してからエクスポートする**:

- **レンダラ**: 単一/分類(categorized)/段階(graduated)/ルールベースは対応。`invertedPolygon`は近似、`heatmap`は対応エンジンのみ、`pointDisplacement`は中心点近似、その他(25d等)は既定スタイルへフォールバック
- **シンボル**: SvgMarker 等の画像は DATA/ へ複製されるが、パス解釈不能なものはフォールバック。`AnimatedMarker`=先頭フレーム静止画。`GeometryGenerator` は常用関数(buffer/translate/centroid/exterior_ring/boundary/convex_hull/envelope)のみ近似、それ以外はスキップ
- **ラベル**: 配置は重心/周囲の近似。`mergeLines`・未配置表示・HTML書式・タブストップ・縦書き(水平代替)・fontSizeMapUnitScale(固定値近似)・ラベル背景画像(矩形代替)・ブレンドモードは未対応/近似。**複雑な注記は QGIS 側で単純化するか、文字列入れ替え前に確定させる**
- **縮尺表示**: レイヤの「縮尺による表示」は `minScale=`/`maxScale=` としてそのまま維持される。WebGIS でも同じ切替になるので、変換時に適切な縮尺帯を設定しておく
- **データ定義プロパティ**: 式の一部のみ評価可。複雑な式は事前に静的な値へ置き換える

## 送出・検証ループ

1. 変換→追加→(必要なら placeLayer で整理)
2. `qgis_bridge_call` → geo_webview `kasugaiExport(engine="cesium", open_app=True)` などでエクスポート&起動
3. **応答の `warnings`/`skipped` を必ず確認** — 未対応レンダラ・解決不能なシンボル・スキップされたレイヤがここに出る。残っていれば変換側を調整して再エクスポート
4. `qgis_screenshot` または Canvas 側で表示確認(色・凡例・ラベル・縮尺帯)

## サイズ・配信の目安

- **GitHub Pages 等の静的ホスト: 1ファイル100MB 上限**。大きいデータは URL 直参照かタイル化/分割する
- ローカル 3D Tiles / XYZ タイルの DATA/ 複製: **1GiB 上限**(超過は skipped)
- DuckDB-WASM 初回ロード約60MBは Service Worker がブラウザ内に永続キャッシュするため、2回目以降は軽い
- 完全サーバレス公開: エクスポート物を静的ホスト(例: kasugai_canvas_webGIS)へ置き、CDN 版エンジンを `…/<channel>/<engine>/?kasc=<.kasc URL>` で開く
