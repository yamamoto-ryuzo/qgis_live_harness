# qgis-webengine-plugin

Qt WebEngine (QWebEngineView + HTML/JS) ベースの QGIS プラグイン開発テンプレート。
UIは通常ブラウザでPlaywrightテスト可能、QGIS実機でもCDP経由でPlaywright接続可能。

## 前提

- QGIS 4.0.1 (`C:\Program Files\QGIS 4.0.1`)
- Node.js 24+
- Python 3.13+ (ユニットテスト用。QGIS同梱Python 3.12不要)

## セットアップ

```powershell
npm install
npm run deploy        # QGISプラグインディレクトリへジャンクション配置+有効化
```

## 使い方

```powershell
npm test              # UI単体E2E(ブラウザ、mock使用)
npm run test:unit     # Pythonロジックのpytest
npm run verify:qgis   # QGISをリモートデバッグ付き起動 → ダイアログを開く
npm run test:live     # 起動中のQGISにPlaywrightで接続して検証
```

詳細は AGENTS.md 参照。
