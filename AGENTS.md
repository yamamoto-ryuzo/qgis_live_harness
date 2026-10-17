# AGENTS.md — AIエージェント向け開発手順

このリポジトリは **Qt WebEngine ベースの QGIS プラグイン**。
プラグインUIは HTML/CSS/JS で実装され、Playwright で自律的に検証できる。

## 構成

- `webengine_plugin/` — QGISプラグイン本体(Python)。QGIS依存は `bridge.py` に閉じ込める
- `webengine_plugin/logic.py` — QGIS非依存の純粋ロジック。pytest対象
- `ui/` — HTML/CSS/JSフロントエンド。QGIS無しの通常ブラウザでも動く(mock使用)
- `ui/src/mock-bridge.js` — Pythonブリッジのモック。**bridgeメソッド追加時は必ず同期更新**
- `tests/e2e/` — Playwrightテスト(L1=mock、L2=実QGIS)
- `tests/unit/` — pytest(logic.py等)

## 検証ループ(変更時はこの順で回す)

```powershell
# L1: UI単体テスト(QGIS不要)。最も頻繁に回す
npm test

# 単体: Pythonロジック
npm run test:unit

# スクリーンショット確認したい場合
npx playwright test --headed   # または test-results/ の画像を見る
```

### L2: 実QGISでの検証(必要時)

```powershell
# 1. プラグイン配置(初回または構成変更時)。ジャンクションなので以後の編集は即反映
npm run deploy

# 2. QGISをCDPデバッグ付きで起動(別ターミナル、開きっぱなし)
#    --code で起動後にプラグインダイアログを自動で開く(-NoAutoOpenで無効化)
npm run verify:qgis

# 3. 実QGISのUIにPlaywrightで接続
npm run test:live
# 接続先変更時: $env:QGIS_CDP_URL="http://localhost:9223"
```

## 重要な制約

- `ui/` は **ESモジュール不可**。`file://` 直読みのため必ずクラシックスクリプト+グローバル名前空間
- `bridge.py` の新メソッドはJSON文字列を返すこと(JS側は `BridgeClient.callJson` で受ける)
- `ui/index.html` の `qrc:///qtwebchannel/qwebchannel.js` はQGIS内でのみ解決可能。通常ブラウザでは読み込み失敗するが正常動作(mockにフォールバック)
- QGISターゲット: **4.0.1**(`C:\Program Files\QGIS 4.0.1`)、Qt6/PyQt6。qgis.PyQt shim経由でimport

## UI確認のコツ

- `page.screenshot()` → PNGはそのまま読んで視覚確認できる
- `page.locator(...).evaluate(...)` でDOM状態を直接確認
- L2では `chromium.connectOverCDP()` で複数contextから `index.html` を含むページを探す
