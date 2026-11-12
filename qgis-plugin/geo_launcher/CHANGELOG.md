# Changelog

## 1.4.0

- **`profile_source_url`**: リモートマニフェスト（`{"version","url","sha256"}`）から配布プロファイルを同期。version が `profiles_version` と同じならスキップ、zip は sha256 検証 + パストラバーサル対策付きで `<settings_dir>/profiles` を丸ごと置換（ミラー）。未設定時は従来のローカル `profiles/` を使用
- **`required_plugins`**: 指定プラグインを対象プロファイルへ自動インストール（実体は同梱せず id/URL のマニフェスト駆動）。`url` 未指定時は公式リポジトリ `plugins.xml` から最新版を解決、インストール後 `QGIS4.ini [PythonPlugins]` を有効化。launch/seed/reset フローに組み込み済み
- bridge `syncProfiles` / `ensurePlugins` を追加（ensurePlugins は現在プロファイルへの導入時に即ロードも試行）

## 1.3.0

- 「起動」ボタンがプロファイルを自動判定するように（「このQGISで開く」ボタンは廃止し起動に統一）
  - 選択プロファイル = 現在のプロファイル → 別プロセスを起動せずこの QGIS でプロジェクトを開く（mount/seed/local_sync の前処理は実行）
  - 選択プロファイル ≠ 現在のプロファイル → 従来通り `qgis --profile` で新プロセス起動
- bridge `launch()` に `mode`(`"auto"`既定/`"process"`/`"in_place"`)と `discard` 引数を追加し同じ判定を実装。戻り値に `mode`/`opened`/`skipped_projects`/`profile_mismatch` を含む
- NSIS 自動更新機能を削除（プラグイン化に伴い更新は QGIS プラグインマネージャーに委ねる）：「更新を確認」「更新を適用」ボタン、bridge `checkUpdate`/`applyUpdate`、`check_nsis_update`/`apply_nsis_update`/`version_is_newer`/`DEFAULT_UPDATE_URL` を除去

## 1.2.0

- 「このQGISで開く」ボタン追加：別プロセスを起動せず現在の QGIS で選択プロジェクトを開く（`iface.addProject` 経由で未保存変更の保存確認あり。プロファイル不一致時は切替不可の警告を表示）
- bridge `openProject(path, discard)` 追加：`"current"`=開き直し、`discard=True` で未保存変更を破棄して置換
- `status()` に `current_profile`/`current_project` を追加

## 1.1.0

- 起動時に現在開いているプロジェクトを渡せるように
  - ダイアログのプロジェクト一覧先頭に「[現在のプロジェクト]」項目を追加（既定で選択・重複パスは除外）
  - bridge `launch()` で `project="current"` を受け付け、`QgsProject.instance().fileName()` へ解決

## 1.0.0

- 初版。kasugai_qgis（Rust 製 QGIS/QField ランチャー）の機能を QGIS プラグインへ移植
- `qgis_settings.json` 読込/保存（force/user オーバーライド・未知キー温存）
- プロファイル/プロジェクト/QGIS・QField バージョン列挙、プロジェクトのバージョンに合った QGIS 自動選択
- ロール customization・global settings ini・startup.py・`PORTAL_USERROLE`・dev mode（`WEBENGINE_*`）付き起動
- `drive_mappings`（subst/rclone sync/rclone mount）・`local_sync`（robocopy /MIR）
- 配布プロファイルのシード/リセット・NSIS 自動更新（SHA-256 検証付き）
- QGIS Live Harness セッション一覧（`~/.qgis-live`）
- `bridge.py`（`GeoLauncherBridge`）で AI 制御フル対応・管理ダイアログ・GeoSuite 共有ツールバー対応
