# AGENTS.md — AIエージェント向け開発手順

このリポジトリは **Qt WebEngine ベースの QGIS プラグイン**。
プラグインUIは HTML/CSS/JS で実装され、2層の自動検証ができる。

## 構成

- `webengine_plugin/` — QGISプラグイン本体(Python)。QGIS依存は `bridge.py` に閉じ込める
- `webengine_plugin/logic.py` — QGIS非依存の純粋ロジック。pytest対象
- `webengine_plugin/live_driver.py` — L2検証用。実QGIS内でJS実行を仲介(後述)
- `ui/` — HTML/CSS/JSフロントエンド。QGIS無しの通常ブラウザでも動く(mock使用)
- `ui/src/mock-bridge.js` — Pythonブリッジのモック。**bridgeメソッド追加時は必ず同期更新**
- `tests/e2e/` — Playwrightテスト(L1=mock)
- `tests/unit/` — pytest(logic.py等)

## 検証ループ(変更時はこの順で回す)

```powershell
# L1: UI単体テスト(QGIS不要)。最も頻繁に回す
npm test

# 単体: Pythonロジック
npm run test:unit
```

### L2: 実QGISでの検証

```powershell
# 1. プラグイン配置(コード変更のたびに必要。コピー型)
npm run deploy          # ※ junctionはこの環境で未確認。-Copyが確実
#   → 使用中プロファイル(profiles.iniのlastProfile)を自動検出して配置+有効化

# 2. QGISを検証モードで起動(別ターミナル、開きっぱなし)
npm run verify:qgis
#   → QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu 等を設定して起動
#   → WEBENGINE_AUTOOPEN でダイアログ自動オープン
#   → WEBENGINE_LIVE_DIR にファイル経由のJS実行チャネルを用意

# 3. 実QGIS内UIを検証
npm run test:live       # test-results/qgis-live.png にスクショも残る
```

## L2の仕組み(重要)

**この環境(QGIS 4.0.1 / QtWebEngine 6.8.1 / Chrome 122)では Playwright は使えない。**
CDPポートは開くが `connectOverCDP` は Browser context 非対応で失敗、
ページ直結wsでも `Runtime.evaluate` が一切応答しない(QtのCDP実装の制限)。

代わりに **ファイル経由ライブドライバ** を使う:

- プラグイン側 `live_driver.py` が `WEBENGINE_LIVE_DIR/qgis-<pid>/commands.jsonl` を
  QTimerでポーリングし、`view.page().runJavaScript()` でJSを実行、
  結果を `results.jsonl` に返す。`screenshot` コマンドは `view.grab()` でPNG保存
- クライアント側 `scripts/live-drive.mjs` (`LivePage`クラス)が
  `evaluate()` / `waitFor()` / `click()` / `screenshot()` を提供。使い勝手はPlaywright相当
- 複数QGISインスタンスが動いていても PID サブディレクトリで分離される

## 環境固有の制約(ハマりやすい点)

- **`QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu --no-sandbox --disable-gpu-compositing` が必須**。
  未設定だとGLESコンテキスト作成に失敗し、レンダラーが死んで
  `loadFinished=False`・`runJavaScript`が常に`None`を返す(verify-in-qgis.ps1で設定済み)
- **`supportsQt6=yes` が metadata.txt に必須**(無いとQt6ビルドがプラグインを読まない)
- **bridgeの重いQGIS操作は `QTimer.singleShot(0, ...)` で遅延させること**。
  WebChannel経由の呼び出しは同期で、重い処理(レイヤーアクティブ化・再描画等)をすると
  レンダラーのJSスレッドがブロックされ後続のrunJavaScriptまで飢餓する(bridge.py参照)
- プラグイン有効化は `QGIS4.ini` の `[PythonPlugins]`。deployスクリプトが自動書き込み
- **.ps1はUTF-8 BOM必須**。BOM無しだとWindows PowerShell 5.1がANSI誤読し、
  日本語コメントの直後の文が実行されない(静かに失敗する)
- `ui/` は **ESモジュール不可**。`file://` 直読みのためクラシックスクリプト+グローバル名前空間
- `bridge.py` の新メソッドはJSON文字列を返す(JS側は `BridgeClient.callJson` で受ける)
- `ui/index.html` の `qrc:///qtwebchannel/qwebchannel.js` はQGIS内でのみ解決可能。
  通常ブラウザでは読み込み失敗するが正常動作(mockにフォールバック)
- QGISターゲット: **4.0.1**(`C:\Program Files\QGIS 4.0.1`)、Qt6/PyQt6。
  `qgis.PyQt` shim経由でimport。`runJavaScript`はQt6で`(script, worldId, callback)`シグネチャ

## UI確認のコツ

- L1(Playwright): `page.screenshot()` のPNGはそのまま読んで視覚確認できる
- L2(LivePage): `page.screenshot(path)` で実QGIS内のUIをPNG化→画像として読める。
  `evaluate()` でDOM状態・bridge呼び出し結果を直接確認できる
- `test-results/plugin_load.log` にプラグイン側の診断ログが残る(環境変数・起動経路)
