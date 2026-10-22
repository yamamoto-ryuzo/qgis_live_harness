# Changelog

## [2.4.0] - 2026-10-23

### Changed
- 自動更新の配信元を GitHub Pages（`yamamoto-ryuzo.github.io/kasugai_qgis`）から harness repo の `raw.githubusercontent.com`（`qgis_live_harness/master/qgis-plugin/kasugai_qgis`）へ移行。`update.json`・`public/` の setup/update/zip が同一 repo から直接配信され、push 直後に反映される。既存インストールの `qgis_settings.json` に旧 Pages URL が残っている場合は起動時に新 URL へ読み替える（`run.py` 側も同様に読み替え）
- 起動時の配布プロファイルコピー（`profiles\QGIS4\` → `%APPDATA%\QGIS\QGIS4\`）を「存在しないファイルのみコピー」から常時上書きに変更。プロファイルはシステム管理のため、全体更新で配布物が更新された場合に必ず利用側へ反映される（dev 配置の junction コピー先は従来通り書き込まない）
- 配布プロジェクトフォルダを `ProjectFiles` → `sample_projects`、サンプルプロジェクトを `ProjectFile.qgs` → `SampleProjectFile.qgs` に改名（同梱 `QGIS4.ini` の Q: 参照・`qgis_settings.json` の既定値も追従）
- 全体版インストーラーにコンポーネント選択ページを追加し、`sample_projects` を「サンプルプロジェクト」として任意インストールに変更（既定は選択。選択を外しても既存フォルダは削除しない。サイレント全体更新では既定どおりインストール）

### Removed
- `download/qgis_launcher.exe`：GitHub Pages 直配布時代の名残り（v2.0.1 コミット済みバイナリ）。現行の配布物は `public/` の setup/update/zip で、`download/` はデータペイロードの正本に役割変更済みのため削除
- `sample_projects/` 内の `3次メッシュ（約1km四方）.gpkg`（対応レイヤ参照は `.qgs` 側で既に除去済み）と QGIS 保存バックアップ `*.qgs~`（インストーラー混入防止）

### Docs
- `download/README.md` を新規作成：ペイロードの役割・各項目のインストール先での扱い（初回のみ/常時上書き/任意コンポーネント）・編集ルールを明文化
- `index.md` 整理：プロファイルコピーの「既存はスキップ」記述を常時上書きへ修正、`C:\qgis_launcher\` 例示を `C:\kasugai\kasugai_qgis\` へ、壊れた `qgis_launcher/download/` リンク修正、パッケージ構成を3配布物（setup/update/zip）の実態へ更新、リリース手順を `run.py --bump` フローへ、GUI起動の WebView2 記述を追加

### Added
- `updata:` による任意ソースからの更新適用。`qgis_launcher.exe updata:<ソース>`（CLI）または `updata:` カスタムプロトコル（HKCU 登録、`kasugai-qgis:` と同様）から起動できる。`.json` 指定は update.json として解釈（sha256 検証あり）、`.exe` 指定はインストーラーとして直接実行（検証なし）。バージョン比較・ループガードは行わず指定物をそのまま適用
- 更新ソースのファイル対応: `update_url`・update.json 内の `url`/`full_url` に http(s) のほか `file://`・ローカルパスを指定可能にした。ローカル update.json 内の相対パスは json の親フォルダ基準で解決する（共有フォルダ配布に対応）
- 既存インストール向けの自動移行: 起動時に `<project_root>/ProjectFiles` があれば `sample_projects` へリネーム（新旧両方がある場合は旧側の未配置エントリのみ移し、空なら旧フォルダを削除）。旧ファイル名 `ProjectFile.qgs*` が残っていれば `SampleProjectFile.qgs*` へ整理。`qgis_settings.json` 内の `project_path`/`current_project` に含まれる `ProjectFiles` パス区切りセグメントは読み込み時に `sample_projects` として解決

## [2.3.0] - 2026-10-22

### Changed
- スタンドアロン起動時の UI 表示を既定ブラウザ（`opener`）から内蔵 WebView2 ウィンドウ（wry/tao）へ変更。既定ブラウザの関連付けに依存せず確実に起動し、ウィンドウを閉じるとサーバーごと終了する。WebView2 Runtime 非搭載環境のみ従来通り既定ブラウザへフォールバック
- 引数なし起動でも UI ウィンドウが開くようにした（従来はサーバーのみ起動して何も表示されなかった）
- `kasugai-qgis:` プロトコル経由の起動は従来通りヘッドレス（ウィンドウを開かない）。残ったタブ・KASUGAI 埋め込みペインが自ら `/health` をポーリングして復帰する方式を維持

### Added
- QGIS Live Harness 連携の開発モード（`dev_mode` 設定 / 起動タブの「開発モード」チェックボックス / CLI `--dev`）。QGIS 起動時に `QTWEBENGINE_REMOTE_DEBUGGING`・`QTWEBENGINE_CHROMIUM_FLAGS`・`WEBENGINE_AUTOOPEN`・`WEBENGINE_LIVE_DIR`・`WEBENGINE_LOG_PATH` を注入し、junction 配置（dev モード）確定時のみ `WEBENGINE_DEV_SRC` も立てる。harness ルートは `KASUGAI_HARNESS_DIR` または exe 祖先の `qgis-plugin/qgis_live_driver/metadata.txt` から検出
- `GET /live-sessions`：`~/.qgis-live` レジストリから稼働中の qgis_live_driver セッションを返し、起動タブに稼働中 PID を表示（i18n キー `label_dev_mode` / `live_session_active` / `live_session_none` を全10言語に追加）
- `scripts/sync_bundle_plugins.py`：`<harness>/qgis-plugin/kasugai_qgis` 配置時、同梱プラグイン（geo_search・geo_webview・geo_report・geo_import・QGIS-legendView-main）を repo 側の正本へミラー同期。`run.py --build` に統合、`--sync-plugins` で単独実行も可

### Changed
- `download/profiles` 同梱の repo 管理プラグインを repo 側の最新へ更新（geo_search 3.3.2→4.4.0、geo_webview 3.10.3→3.17.0、geo_report 2.2.6→2.9.0、geo_import V2.3.45→2.10.0、QGIS-legendView-main 2.0.16→2.6.1）

### Fixed
- `--cli` 起動時に配布プロファイルのコピー（`copy_profiles_at_startup`）が実行されず、未シード環境で `--profile` が空プロファイルを指していた問題を修正
- `GET /profiles` が配布側 `profiles/QGIS{major}` バージョン別コンテナや空ディレクトリをプロファイル名として誤列挙していた問題を修正（`QGIS{major}/profiles/` 内を実プロファイルとして列挙）
- `GET /live-sessions` で dead セッションの stale レジストリ（`~/.qgis-live/*.json`）を自動削除するようにした（起動直後120秒以内のファイルは誤削除防止のため保持）

## [2.2.1] - 2026-10-07

### Changed
- 「Axum サーバーを停止」ボタンを赤色に変更し、誤操作しにくい見た目にした
- サーバー停止の確認ダイアログに「停止するとこの画面は操作できなくなる」旨を追記（全10言語）
- サーバー停止後の案内画面を「再起動するか閉じるか」の選択肢が分かる文言に更新（全10言語）

## [2.2.0] - 2026-10-06

### Added
- カスタムプロトコル `kasugai-qgis:` を HKCU に自己登録し、サーバー停止後に残ったブラウザタブからランチャーを再起動できるようにした
  - サーバー未接続時に「ランチャーを再起動」ボタンを表示し、起動後は `/health` をポーリングしてタブを自動リロード
  - プロトコル URI は `Args` の位置引数 `uri` で受け取り、トリガーとしてのみ使用
- サーバー停止後にタブを `window.close()` で閉じる試行を追加。ブラウザにブロックされた場合は「このタブは閉じて構いません」の案内画面へ置き換え（QGIS 起動後 / サーバー停止ボタン / 更新適用の3経路）

### Changed
- サーバー未接続時のエラーメッセージを生の `Failed to fetch` から分かりやすい案内文へ変更（i18n キー `status_server_unreachable` を全10言語に追加）

### Fixed
- `qgis_settings.json` の `QgisSettings` への変換失敗がサイレントにデフォルト値へフォールバックしていた問題を修正し、ファイルパスと理由を stderr に出力するようにした

## [2.1.0] - 2026-10-06

### Added
- Web UI の多言語対応（i18n）を導入
  - `public/i18n.js` と 10 言語の辞書（en 正本 / ja, zh, zh-tw, ko, es, fr, de, pt, ru）
  - タブバーに言語切替セレクタを追加（localStorage で永続化、初期値はブラウザ言語から検出）
- AGENTS.md を追加（作業ルール・テスト手順・言語方針）

### Changed
- 起動タブのフィールド順を プロジェクト→プロジェクトファイルバージョン→QGIS バージョン に変更
- プロジェクトのバージョンに一致する QGIS が無い場合、メッセージを出してシステム既定（.qgs 関連付け）へフォールバックする旨を明示

### Fixed
- QGIS バージョンが未選択になる問題を修正（レジストリ取得の 8.3 短縮パスを正規化し、設定値が選択肢に一致しない場合は先頭を選択）
- `GET /update` が tokio パニックで空応答になる問題を修正（`check_nsis_update` を `spawn_blocking` へ移動）

## [2.0.5] - 2026-10-06

### Changed
- QGIS 起動後（`POST /launch`）にランチャーサーバーを自動停止するように変更
- Web UI の起動時メッセージをサーバー自動停止の案内に更新

## [2.0.2] - 2026-07-29

### Added
- EXE アイコン埋め込み（`build.rs`）
- ファビコン配信用エンドポイント
- ブラウザ自動起動機能
- 多重起動防止機能

### Changed
- Windows サブシステム化
- インストーラー・ショートカットを AGENTS.md 仕様に合わせて整備
  - ショートカットに `--open-browser` オプションを付与
  - `RequestExecutionLevel` を `admin` に修正
- `update.json` を 2.0.2 に更新

## [2.0.1] - 2026-07-29

### Removed
- QGIS3 プロファイルサポートを削除
  - `download/profiles/QGIS4/profiles/geo_custom/QGIS/QGIS3.ini` を廃止

### Changed
- QGIS バージョン自動検出と QGIS4 プロファイル配信を一本化
- Web UI (`public/index.html`) を QGIS4 仕様に更新
- `index.md` ドキュメントを 2.0.1 仕様に更新
- `update.json` のバージョンを 2.0.1 に更新

## [2.0.0] - 2026-07-29

### Added
- AXUM ベースの HTTP API サーバー機能を追加
  - `GET /` — 操作 UI (`public/index.html`) を返す
  - `GET /health` — 生存確認
  - `GET /settings` / `POST /settings` — 設定読み書き
  - `GET /profiles` / `GET /projects` / `GET /qgis` — 選択候補一覧
  - `POST /launch` — QGIS 起動
  - `POST /reset` — プロファイル初期化
  - `GET /project-version` — プロジェクトファイルの QGIS バージョン取得
  - `GET /update` / `POST /update/apply` — 手動更新確認・適用
  - `GET /api/v1/server/info` — サーバー情報取得
  - `POST /api/v1/server/stop` — サーバー停止
- ブラウザベースの操作 UI (`public/index.html`)
  - タブ形式：起動 / 探索パス / 詳細設定 / 設定
  - プロファイル・QGIS バージョン・プロジェクトのドロップダウン選択
  - 生 JSON エディタによる `qgis_settings.json` 直接編集
  - `project_root` と API 待ち受けポートの編集・保存
  - サーバー停止ボタン
- 新しい CLI 引数 `--server` / `--port`（Tauri サイドカー対応）

### Changed
- API サーバーモードは `--server` オプションで有効化。未指定時は QGIS を通常起動する
- 待ち受けポートのデフォルトを 8500 に統一し、`qgis_settings.json` の `api_server_port` も参照
- `project_root` 解決時、対象フォルダ内に `qgis_settings.json` があれば再読み込み
- `reset_profiles` およびローカル自動同期の対象ディレクトリを `project_root` に統一

### Removed
- FLTK ベースの GUI を削除
- `fltk` 依存と `gui` feature を削除

## [1.4.1] - 2026-07-25

### Changed
- バージョンを 1.4.1 に更新

## [1.4.0] - 2026-07-25

### Added
- NSIS ベースの自動更新機能を追加
  - `qgis_settings.json` に `update_url` と `update_check` を設定することで、起動時にリモートの `update.json` を確認
  - 新しいバージョンがあれば NSIS インストーラーをダウンロードして実行し、自身を更新
  - 更新後は新しいプロセスを起動して終了する
- GitHub Pages 用の標準更新 URL を設定
  - `update_url`: `https://yamamoto-ryuzo.github.io/kasugai_qgis/update.json`
- `installer/setup.nsi`: 本体 `qgis_launcher.exe` のみを更新する軽量 NSIS インストーラースクリプト
- `installer/build.bat`: NSIS インストーラー生成バッチ
- `update.json`: GitHub Pages 配信用更新情報ファイル
- `download/kasugai_qgis_1.4.0_x64-setup.exe`: 初版リリース用 NSIS インストーラー

### Changed
- `download/qgis_settings.json` の例に `update_url` と `update_check` を追加

---

## [1.x.x] 以前

- QGIS / QField 起動ランチャー機能
- プロファイル・プロジェクト・QGIS バージョン選択 GUI
- ユーザーロール制御（Viewer / Editor / Administrator）
- クラウドドライブ自動割り当て（`drive_mappings`）
- ローカル自動同期（`local_sync` / `qgislocalsync.config`）
