# CDPリモートデバッグを有効にしてQGISを起動する。
# 起動後、プラグインのダイアログを開けば npm run test:live でPlaywrightが接続できる。

param(
  [string]$QgisExe = "C:\Program Files\QGIS 4.0.1\bin\qgis-bin.exe",
  [int]$DebugPort = 9222,
  [switch]$NoAutoOpen
)

if (-not (Test-Path $QgisExe)) {
  Write-Error "QGIS not found: $QgisExe"
  exit 1
}

$env:QTWEBENGINE_REMOTE_DEBUGGING = "$DebugPort"
# この環境ではGLESコンテキスト作成に失敗しレンダラーが死ぬためGPU無効化が必須
$env:QTWEBENGINE_CHROMIUM_FLAGS = "--disable-gpu --no-sandbox --disable-gpu-compositing"
if (-not $NoAutoOpen) {
  $env:WEBENGINE_AUTOOPEN = "1"
  # LiveDriver(ファイル経由JS実行)の作業ディレクトリを指定
  $env:WEBENGINE_LIVE_DIR = Join-Path (Split-Path -Parent $PSScriptRoot) "test-results\live"
  $env:WEBENGINE_LOG_PATH = Join-Path (Split-Path -Parent $PSScriptRoot) "test-results\plugin_load.log"
}
Write-Host "Launching QGIS with QTWEBENGINE_REMOTE_DEBUGGING=$DebugPort"
Write-Host "  -> $QgisExe"

if ($NoAutoOpen) {
  & $QgisExe
} else {
  # startup.py がダイアログを自動で開く(未導入なら install-startup.ps1 を先に実行)
  & $QgisExe
}
