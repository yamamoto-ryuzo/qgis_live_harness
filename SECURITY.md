# Security Policy

## 脆弱性の報告

このプロジェクトのセキュリティ上の問題を発見した場合は、**公開のIssueやPull Requestではなく**、
GitHubリポジトリのメンテナ(@yamamoto-ryuzo)へ個別にご連絡ください。

報告に含めていただきたい情報:

- 影響を受けるコンポーネント(`qgis_live_driver` / Harnessスクリプト 等)とバージョン
- 再現手順または攻撃シナリオの説明
- 想定される影響範囲

## セキュリティモデル

`qgis_live_driver` は `pyeval`(QGISプロセス内での任意Python実行)を提供する
**localhost限定のリモート制御プラグイン**です。脅威モデル・認証方式・防御の限界の
詳細はドキュメントを参照してください:

- セキュリティモデル: <https://yamamoto-ryuzo.github.io/qgis_live_harness/security.html>
- Driver詳細: <https://yamamoto-ryuzo.github.io/qgis_live_harness/driver.html>

要点:

- HTTP は `127.0.0.1` にのみバインド(外部ネットワークから到達不能)
- 全チャネル(HTTP/MCP/ファイルJSONL)でセッショントークン必須
- トークンはユーザ限定ACLのファイルにのみ保存(信頼境界=ローカルユーザアカウント)
- **同一ユーザ権限のプロセスは防げない**(あらゆるlocalhostサービスの限界)

## 対象バージョン

最新リリースバージョンのみサポートします。
