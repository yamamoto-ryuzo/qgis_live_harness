# 翻訳ファイルの更新方法

## 概要
このプラグインは、QGISの設定言語を自動検出し、10言語に対応しています：
- 英語 (en)
- フランス語 (fr)
- ドイツ語 (de)
- スペイン語 (es)
- イタリア語 (it)
- ポルトガル語 (pt)
- 日本語 (ja)
- 中国語 (zh)
- ロシア語 (ru)
- ヒンディー語 (hi)

## 翻訳の仕組み

### 1. ソースコード
- UIファイル（.ui）の文字列は英語で記述
- Pythonコード内で表示する文字列は `tr()` メソッドで囲む
- 例: `self.tr("Search")` または `Util.tr("Settings")`

### 2. 翻訳ファイル（TS）
- `geo_import/i18n/` ディレクトリに各言語のTSファイルがあります
- TSファイルはXML形式で、翻訳前の文字列と翻訳後の文字列を含みます

### 3. コンパイル済み翻訳ファイル（QM）
- TSファイルから生成されるバイナリファイル
- QGISが実際に使用する翻訳ファイル

## 翻訳の更新手順

### 方法1: バッチファイルを使用（推奨）
Windowsの場合、プロジェクトルートにある `lrelease_all.bat` を実行します：

```batch
cd c:\github\geo_import
lrelease_all.bat
```

### 方法2: Pythonスクリプトを使用
`geo_import` ディレクトリで以下のスクリプトを実行：

```bash
cd geo_import
python generate_qm.py
```

## 新しい翻訳の追加方法

### 1. TSファイルを編集
各言語のTSファイル（例：`i18n/geo_import_ja.ts`）を開き、新しい翻訳エントリを追加：

```xml
<message>
    <source>Original English Text</source>
    <translation>翻訳されたテキスト</translation>
</message>
```

### 2. QMファイルを再生成
上記の方法1または方法2でQMファイルを再生成します。

## Qt Linguistを使用した翻訳編集

より視覚的に翻訳を編集したい場合は、Qt Linguistを使用できます：

```batch
C:\Qt\linguist_6.9.1\linguist.exe geo_import\i18n\geo_import_ja.ts
```

Qt Linguistで翻訳を編集し、保存した後、QMファイルを再生成してください。

## 開発者向け情報

### lreleaseのパス
現在の設定：`C:\Qt\linguist_6.9.1\lrelease.exe`

別の場所にインストールされている場合は、以下のファイルを更新してください：
- `lrelease_all.bat` の `LRELEASE` 変数
- `geo_import/generate_qm.py` の `LRELEASE_PATH` 変数

### 翻訳コンテキスト
翻訳は以下のコンテキストに分類されています：
- `GeoImport` - メインプラグインクラス
- `GeoImportDialogBase` - メインダイアログのUI要素

## トラブルシューティング

### QMファイルが生成されない
1. lreleaseのパスが正しいか確認
2. TSファイルのXML形式が正しいか確認（閉じタグ等）
3. エラーメッセージを確認

### 翻訳が表示されない
1. QMファイルが `i18n/` ディレクトリに存在するか確認
2. QGISの言語設定を確認
3. プラグインを再読み込み
