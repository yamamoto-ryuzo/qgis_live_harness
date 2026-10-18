# CDPリモートデバッグを有効にしてQGISを起動する。
# 起動後、プラグインのダイアログを開けば npm run test:live でPlaywrightが接続できる。

param(
  [string]$QgisExe = "",
  [int]$DebugPort = 9222,
  [switch]$NoAutoOpen
)

# 未指定なら C:\Program Files\QGIS* の最新版を自動検出
if (-not $QgisExe) {
  $cand = Get-ChildItem "$env:ProgramFiles\QGIS*\bin\qgis-bin.exe" -ErrorAction SilentlyContinue |
    Sort-Object FullName -Descending | Select-Object -First 1
  if ($cand) { $QgisExe = $cand.FullName }
}

if (-not $QgisExe -or -not (Test-Path $QgisExe)) {
  Write-Error "QGIS not found. Pass -QgisExe or set QGIS_EXE."
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
  # リポジトリ側のbridge/uiを直接読むdevモード(live:devreloadが有効になる)
  $env:WEBENGINE_DEV_SRC = (Split-Path -Parent $PSScriptRoot)
}
Write-Host "Launching QGIS with QTWEBENGINE_REMOTE_DEBUGGING=$DebugPort"
Write-Host "  -> $QgisExe"

if ($NoAutoOpen) {
  & $QgisExe
} else {
  # startup.py がダイアログを自動で開く(未導入なら install-startup.ps1 を先に実行)
  & $QgisExe
}
