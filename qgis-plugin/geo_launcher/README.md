# geo_launcher

[kasugai_qgis](https://github.com/yamamoto-ryuzo/kasugai_qgis)（Rust 製 QGIS/QField ランチャー）の機能を QGIS プラグインとして移植したものです。QGIS の中から、別の QGIS/QField インスタンスをプロファイル・プロジェクト・バージョン・ユーザーロール指定で起動できます。

## 主な機能

- `qgis_settings.json` の読み込み・保存（`qgis_settings_override.json` / `qgis_settings_<USERNAME>.json` のオーバーライド対応・未知キー温存）
- プロファイル一覧（配布 `profiles/` + `%APPDATA%\QGIS\QGIS4\profiles`）
- プロジェクト一覧（`project_path` から `.qgs/.qgz` を解決）
- QGIS/QField 実行ファイル列挙（レジストリ関連付け・Program Files・OSGeo4W・ポータブル版）
- プロジェクトの `<qgis version>` に合った実行ファイルの自動選択
- 起動時の注入: `PORTAL_USERROLE`、`--profile`、`--customizationfile`（`ini/<role>.xml`）、`--globalsettingsfile`、`--code ini/startup.py`、開発モード時は `WEBENGINE_*`（QGIS Live Harness 連携）
- `drive_mappings`: subst / rclone sync / rclone mount
- `local_sync`: robocopy `/MIR` によるローカル自動同期（バージョンファイル管理）
- 配布プロファイルのシード / リセット
  - `profile_source_url`: リモートマニフェスト（version/url/sha256）から配布プロファイルを同期（CDN/GitHub Pages 等からの配布に対応）
  - `required_plugins`: `[{"id":"geo_search"},{"id":"x","url":"...","sha256":"..."}]` — 指定プラグインを公式リポジトリ/任意URLから対象プロファイルへ自動インストール（実体は同梱しない）
- QGIS Live Harness セッション一覧（`~/.qgis-live`、TCP 生存判定）

## 使い方

1. `プラグイン > geo_launcher > QGIS/QField launcher...`（または GeoSuite ツールバーのアイコン）でダイアログを開く
2. 「Launcher folder」に `qgis_settings.json` のあるフォルダを指定（既定は `C:\kasugai\kasugai_qgis` 等を自動検出）
3. 実行ファイル・プロファイル・プロジェクト・ロールを選んで「Launch」

起動時は Rust 版と同じフローで `drive_mappings` → プロファイルシード → `local_sync` → QGIS 起動の順に実行されます。

## AI / 外部制御（bridge）

`GeoLauncherBridge` が `plugin.bridge` に配線されており、`qgis_live_driver` の `bridge_call` / `describe_plugins` から利用できます。

```text
qgis_bridge_call pluginId="geo_launcher" method="pluginInfo"
qgis_bridge_call pluginId="geo_launcher" method="launch" args=["geo_custom"]
qgis_bridge_call pluginId="geo_launcher" method="listProfiles"
qgis_bridge_call pluginId="geo_launcher" method="setSettings" args=[{"dev_mode": true}]
```

主なメソッド: `pluginInfo` / `status` / `settingsDir` / `getSettings` / `setSettings` / `listProfiles` / `listProjects` / `listVersions` / `listSessions` / `projectVersion` / `launch` / `mountDrives` / `localSync` / `seedProfiles` / `resetProfiles`（`confirm=True` 必須）/ `checkUpdate` / `applyUpdate` / `openDialog` / `closeDialog`

## ライセンス

GPL-3.0（[LICENSE](LICENSE)）
