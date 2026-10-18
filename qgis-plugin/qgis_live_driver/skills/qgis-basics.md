# QGIS pyeval 基本レシピ

qgis_pyeval での典型的なQGIS操作パターン。GUIスレッドで実行され、
`iface` / `QgsProject` / `QgsApplication` / `driver` がスコープに入る。
式なら値が返り、文なら `result` への代入値が返る。

## プロジェクト・レイヤ

```python
# レイヤ一覧
result = [l.name() for l in QgsProject.instance().mapLayers().values()]

# 名前でレイヤを取得
layers = QgsProject.instance().mapLayersByName("レイヤ名")
layer = layers[0] if layers else None

# 現在のキャンバス範囲・縮尺
c = iface.mapCanvas()
result = {"extent": str(c.extent().toString()), "scale": c.scale()}
```

## 地物の読み込み

```python
# 選択地物の属性
layer = iface.activeLayer()
result = [f.attributes() for f in layer.selectedFeatures()][:50]

# 件数のみなら getFeatures は iterator を作るだけで軽い
result = sum(1 for _ in layer.getFeatures())
```

## 表示の確認

- 変更後は `iface.mapCanvas().refresh()` で再描画し、
  `qgis_screenshot` で目視確認する
- 凡例/レイヤツリーは `iface.layerTreeView()`

## プラグインの操作

```python
# ロード済みプラグインに直接アクセス
import qgis.utils
p = qgis.utils.plugins.get("geo_search")
# plugin.bridge を持つものは bridge_call 経由が安全
```
