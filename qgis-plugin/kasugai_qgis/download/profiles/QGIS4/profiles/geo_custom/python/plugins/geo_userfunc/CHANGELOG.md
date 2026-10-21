# CHANGELOG — geo_userfunc

## 1.0.0

- 初版。ユーザー定義Pythonコードのライブラリ管理プラグイン
- `<profile>/python/geo_userfunc/` の `*.py` をASTで型分類:
  - `@qgsfunction` → 式エンジンへ登録(関数型)
  - `openProject`/`saveProject`/`closeProject` → プロジェクト信号へ配線(フック型)
  - `main(context)` → 手動実行マクロ(メニュー/bridge run)
- 共有レジストリ(`plugin.registry`)で他プラグインのマクロを一元管理
  (pull: `register_user_functions(registry)` 規約の探索 / push: 直接登録)
- bridge(`GeoUserfuncBridge`)でAI制御にフル対応:
  `listFunctions`/`listMacros`/`run`/`evalExpression`/`readFunction`/
  `saveFunction`/`deleteFunction`/`setEnabled`/`reload`/
  `updateFromUpstream`/`status`/`openManager`
- 管理ダイアログ(一覧/有効化/編集/フォルダ表示/URL取得/upstream更新)、
  GeoSuite共有ツールバーに起動アクションを集約
- 初期ライブラリとして QGIS_user_function(upstream)の `python` を
  `user_functions.py` として同梱・初回シード
  (sources.json による upstream 追従更新対応)
