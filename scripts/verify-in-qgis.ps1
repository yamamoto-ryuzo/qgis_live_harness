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
  # WEBENGINE_DEV_SRC(repo側bridge/uiを直接読むdev機構)は
  # devモード=junction配置の確定時のみ立てる。実体dir(利用版)が
  # 1つでもあれば立てない(利用版へrepoコードが混入するため)
  $repoRoot = Split-Path -Parent $PSScriptRoot
  $prof = "default"
  $profilesIni = Join-Path "$env:APPDATA\QGIS\QGIS4\profiles" "profiles.ini"
  if (Test-Path $profilesIni) {
    $m = Select-String -Path $profilesIni -Pattern "lastProfile=(.+)"
    if ($m) { $prof = $m.Matches.Groups[1].Value.Trim() }
  }
  $pluginsRoot = Join-Path "$env:APPDATA\QGIS\QGIS4\profiles\$prof" "python\plugins"
  $sawDir = $false
  $sawJunction = $false
  Get-ChildItem (Join-Path $repoRoot "qgis-plugin") -Directory |
    Where-Object { Test-Path (Join-Path $_.FullName "metadata.txt") } |
    ForEach-Object {
      $dst = Join-Path $pluginsRoot $_.Name
      if (Test-Path $dst) {
        if ((Get-Item $dst -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
          $sawJunction = $true
        } else {
          $sawDir = $true
        }
      }
    }
  if ($sawJunction -and -not $sawDir) {
    $env:WEBENGINE_DEV_SRC = $repoRoot
  } else {
    Write-Host "  devモード(junction配置)以外のため WEBENGINE_DEV_SRC 未設定" +
      "(配置済み実体dirが動作)"
  }
}
Write-Host "Launching QGIS with QTWEBENGINE_REMOTE_DEBUGGING=$DebugPort"
Write-Host "  -> $QgisExe"

if ($NoAutoOpen) {
  & $QgisExe
} else {
  # startup.py がダイアログを自動で開く(未導入なら install-startup.ps1 を先に実行)
  & $QgisExe
}
