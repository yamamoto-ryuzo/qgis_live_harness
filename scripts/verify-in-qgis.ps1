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
Write-Host "Launching QGIS with QTWEBENGINE_REMOTE_DEBUGGING=$DebugPort"
Write-Host "  -> $QgisExe"

if ($NoAutoOpen) {
  & $QgisExe
} else {
  # 起動後にプラグインダイアログを自動で開く
  $openScript = Join-Path $PSScriptRoot "open_plugin_dialog.py"
  & $QgisExe --code $openScript
}
