# Changelog

このプロジェクトの注目すべき変更はすべてこのファイルに記録します。
フォーマットは [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/)、
バージョニングは [Semantic Versioning](https://semver.org/lang/ja/) に準拠します。

## [Unreleased]

## [1.1.0] - 2026-10-18

### Added

- `scripts/setup.ps1`(`npm run setup`): 初回クローン後の一括セットアップ。
  前提ツール(QGIS 4.x / Node.js 24+ / Python 3.13+ / pytest)を確認し、
  不足分をwinget経由でインストールした上で `npm install` →
  `npx playwright install` → `npm run deploy:copy` を実行する
  (`-Yes` / `-CheckOnly` / `-SkipPlaywright` / `-SkipDeploy`)

## [1.0.0] - 2026-10-18

初回公開リリース。QGISプロセスをAI/外部スクリプトから自律駆動するための
開発・制御・検証基盤 **QGIS Live Harness**(このリポジトリ)と、QGIS内に常駐する
制御プラグイン **QGIS Live Driver** を含む。

同梱プラグインはリポジトリとは別のバージョン系で管理する:

- `qgis_live_driver`: 0.2.0 (experimental)
- `webengine_plugin` (サンプル): 0.1.0 (experimental)

### Added

- **QGIS Live Driver** (`qgis-plugin/qgis_live_driver`): QGIS内で動く制御専用プラグイン
  - ファイルJSONL(`commands.jsonl` → `results.jsonl`)によるコマンド実行
    (`eval` / `pyeval` / `screenshot` / `devreload` / `status` /
    `open_plugin` / `reload_plugin` / `bridge_call`)
  - REST `/api/*` と MCP Streamable HTTP `/mcp`(127.0.0.1バインド)、
    同梱stdio shim `mcp_stdio.py`(Node不要)
  - `plugin_id` ルーティング(hub): 1つのlive dir/HTTPポートから
    live中の全プラグインを制御
  - セキュリティ: 全チャネルでセッショントークン認証必須、Host/Originの
    loopbackチェック、`QGIS_LIVE_API_KEY` / `QGIS_LIVE_TOOLS` env、
    QSettings永続化のリモート制御トグル(既定オフ・初回警告付き)
- **QGIS Live Harness**(リポジトリ基盤)
  - `scripts/live-drive.mjs` (`LivePage`): Playwright相当の
    evaluate / pyeval / screenshot / waitFor / click / devreload 等のクライアントAPI
  - `scripts/qgis-session.mjs`: ensure(起動中へのアタッチ/自動起動) /
    reload / devreload
  - `scripts/qgis-mcp.mjs`: 上記経路をMCPツールとして公開するstdioサーバ
    (`qgis_ensure` / `qgis_pyeval` / `qgis_eval` / `qgis_bridge_call` /
    `qgis_screenshot` / `qgis_status` / `qgis_open_plugin` /
    `qgis_devreload` / `qgis_reload`)
  - `npm run live:*` / `test:live` / `deploy` / `new:plugin` コマンド群
  - 複数QGISインスタンス・複数プラグインのlive dir分離
    (`qgis-<pid>/<plugin_id>`)
  - `plugin.config.json` による開発対象プラグイン切替、
    `scripts/new-plugin.mjs` によるプラグイン雛形生成
- **サンプルプラグイン** `webengine_plugin`: QWebEngineView + QWebChannel
  bridge構成の雛形(mock-bridgeによるQGIS無しのUI単体動作付き)
- **検証基盤**: L1 Playwright(`npm test`)、pytest(`tests/unit`)、
  実QGIS検証 `test:live`
- **ドキュメント**: GitHub Pages用 `docs/`(概要 / 使い方 / セキュリティ /
  Driver / Harness / 配布 / internals)、AGENTS.md、SECURITY.md、
  THIRD_PARTY_LICENSES.md
- ライセンス: GPL-2.0-or-later

### Fixed

- `mcp_stdio.py` の serverInfo バージョンを `mcp_http.py` / metadata.txt に
  合わせ 0.2.0 に修正

[Unreleased]: https://github.com/yamamoto-ryuzo/qgis_live_harness/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/yamamoto-ryuzo/qgis_live_harness/releases/tag/v1.0.0
