# CDPリモートデバッグを有効にしてQGISを起動する。
# 起動後、プラグインのダイアログを開けば npm run test:live でPlaywrightが接続できる。

param(
  [string]$QgisExe = "C:\Program Files\QGIS 4.0.1\bin\qgis-bin.exe",
  [int]$DebugPort = 9222
)

if (-not (Test-Path $QgisExe)) {
  Write-Error "QGIS not found: $QgisExe"
  exit 1
}

$env:QTWEBENGINE_REMOTE_DEBUGGING = "$DebugPort"
Write-Host "Launching QGIS with QTWEBENGINE_REMOTE_DEBUGGING=$DebugPort"
Write-Host "  -> $QgisExe"
& $QgisExe
