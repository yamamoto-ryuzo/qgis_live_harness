# 使用コンポーネントとライセンス一覧

このリポジトリ自体のライセンスは **GPL-2.0-or-later**([LICENSE](LICENSE))。
選択理由: QGISプラグイン(`qgis-plugin/*`)は実行時に QGIS(GPL-2.0+)・
PyQt6(GPLv3)へリンクする派生物であり、配布時はGPL系の適用が実質必須のため。

## 実行時依存(QGIS本体が提供・同梱はしない)

| コンポーネント | 用途 | ライセンス |
|---|---|---|
| QGIS 4.0.x | プラグインの実行ホスト | GPL-2.0-or-later |
| PyQt6 (`qgis.PyQt`) | Qtバインディング | GPLv3 |
| Qt 6 / QtWebEngine | UI描画(QWebEngineView) | LGPLv3 |

これらは利用者のQGISインストールに含まれるものであり、
本リポジトリはソース・バイナリとも同梱しない。

## 開発・テスト依存(配布物に含まれない)

npm(`package.json` devDependencies、`npm install` で取得):

| パッケージ | 用途 | ライセンス |
|---|---|---|
| `@modelcontextprotocol/sdk` | MCPサーバ(`scripts/qgis-mcp.mjs`) | MIT |
| `@playwright/test` (+playwright/playwright-core) | L1 UIテスト | Apache-2.0 |
| 上記の推移依存(ajv, zod, hono 等) | — | MIT / ISC / BSD-2-Clause / BSD-3-Clause |

その他:

| コンポーネント | 用途 | ライセンス |
|---|---|---|
| pytest | `npm run test:unit` | MIT |
| mermaid@11 | docs/`*.html` 閲覧時にCDN(jsdelivr)から読込。バンドルなし | MIT |

## 自著作部分

- `qgis-plugin/`(プラグインコード)、`scripts/`、`docs/`、`tests/`、
  `ui/` 内のJS/CSSはすべて本プロジェクトのオリジナルで、
  第三者コードの同梱(vendoring)はない。
