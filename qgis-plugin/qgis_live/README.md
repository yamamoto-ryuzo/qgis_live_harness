# QGIS Live Driver (`qgis_live`)

実行中のQGISプロセスを**外部アプリから遠隔操作**するための、
UIを持たない制御専用プラグイン。
リポジトリの「機能1: APIによる各種アプリからの遠隔操作(基盤)」を
**プラグイン単体の形にしたもの**。

`webengine_plugin` と違い `QWebEngineView` を持たないため、
**WebEngineを使わない任意のQGIS環境・任意の他プラグイン**に対しても
`pyeval` 経由の遠隔操作面を提供できる。

## できること

| コマンド | 動作 |
|---|---|
| `pyeval` | QGISプロセス内で任意Pythonを同期実行し結果を返す。名前空間に `iface` / `QgsProject` / `QgsApplication` / `driver` を持つ → `iface.activeLayer().name()` や `QgsProject.instance().mapLayers()` 等で内部状態を直接取得・操作できる |
| `screenshot` | `iface.mapCanvas().saveAsImage(path)` で地図キャンバスをPNG保存 |
| `eval` / `devreload` | viewを持たないため **unsupported エラーを返す**(ハングしない) |

## 仕組み

環境変数 `WEBENGINE_LIVE_DIR` が設定された状態でQGISが起動すると、
`initGui` 時に `live_driver.py` が起動し
`WEBENGINE_LIVE_DIR/qgis-<pid>/qgis_live/` をポーリングする:

```
外部アプリ → commands.jsonl に1行1JSONを追記
           → QTimer(200ms)が読み取り実行
           → results.jsonl に {id, result|error} を追記で返却
```

- 輸送層はファイルのみ。**言語非依存**(JSON Linesを追記・読取できれば何でもよい)
- `commands.jsonl` は **append-only**。切り詰めるとドライバのoffsetが
  ずれてmid-line読み(JSONDecodeError+コマンド喪失)を起こす
- 同一live dirへの同時アクセスは **単一クライアント** 前提

## 有効化

```powershell
# このリポジトリから(全プラグイン一括deploy)
powershell -ExecutionPolicy Bypass -File scripts/deploy-plugin.ps1 -Copy

# または手動: このフォルダを python/plugins/qgis_live/ へコピーし、
# QGISのプラグイン管理で有効化
```

起動時に `WEBENGINE_LIVE_DIR` が必要(未設定なら何もしない無害なプラグイン):
`scripts/verify-in-qgis.ps1` が付与して起動する。

## セキュリティ

`pyeval` は **任意コード実行**。**開発専用**であり、
エンドユーザーへの配布物に含めてはいけない
(metadata.txtにも `Development-only` と明記済み)。
