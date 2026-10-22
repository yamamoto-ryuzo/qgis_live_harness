# download/ — 配布ペイロードの正本

このフォルダは **インストーラー・配布 ZIP に同梱されるデータ一式の正本**です。
ランタイム配置ではなく、以下のビルドから参照されます:

| ビルド | 取り込み内容 |
|---|---|
| `installer/setup.nsi`（全体版 `kasugai_qgis-setup.exe`） | 全ファイル + 全フォルダ |
| `installer/setup.nsi`（EXEのみ版 `kasugai_qgis-update.exe`、`/DUPDATE_ONLY`） | 何も取り込まない（EXE のみ） |
| `installer/build_zip.bat` / `run.py` の ZIP ステージング | 全ファイル + 全フォルダ |

## 構成

| 項目 | インストール先での扱い | 内容 |
|---|---|---|
| `qgis_settings.json` | **初回のみ配置**（既存は上書きしない） | 全設定の起点。`profile`/`project_path`/`drive_mappings`/`local_sync`/`update_url` 等 |
| `ini/` | 常時上書き（システム管理） | ユーザーロール制御。`<role>.xml`（`--customizationfile`）・`qgis_global_settings.ini` 雛形・`startup.py`（`--code`） |
| `profiles/` | 常時上書き（システム管理） | 配布 QGIS プロファイル `QGIS4/profiles/geo_custom/`。起動毎に `%APPDATA%\QGIS\QGIS4\` へ既存ファイルも上書きコピー。repo 管理プラグイン 5 本は `scripts/sync_bundle_plugins.py` が `qgis-plugin/<id>` からミラー |
| `sample_projects/` | **任意コンポーネント**（インストール時に要否選択可。既定は選択） | `SampleProjectFile.qgs` + `data/` + `symbol/`。`project_path` の既定探索先 |
| `*.example` ×3 | 常時上書き | `qgis_settings_override` / `qgis_settings_{USERNAME}` / `qgislocalsync.config` の記述例 |

## ルール

- **ここに実行バイナリは置かない**（本体は `target/release/qgis_launcher.exe` を使う。
  かつて Pages 直配布用に `download/qgis_launcher.exe` をコミットしていたが廃止）
- QGIS 保存時に生成されるバックアップ（`*.qgs~` 等）は残さない。`File /r` で
  インストーラーに混入するため
- `profiles/` 配下の repo 管理プラグインは直接編集しない。正本は `qgis-plugin/<id>` で、
  変更は `python run.py --sync-plugins`（または `--build`）でここへ同期する
