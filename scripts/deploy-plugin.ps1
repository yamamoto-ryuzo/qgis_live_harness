# プラグインをQGISのプラグインディレクトリへ配置する。
# 既定ではジャンクション(管理者権限不要)を張り、失敗した場合はコピーする。
# QGISプロファイルのプラグイン有効化([PythonPlugins] webengine_plugin=true)も行う。

param(
  [string]$QgisProfileRoot = "$env:APPDATA\QGIS\QGIS4\profiles\default",
  [switch]$Copy
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$pluginSrc = Join-Path $repoRoot "webengine_plugin"
$pluginDst = Join-Path $QgisProfileRoot "python\plugins\webengine_plugin"

New-Item -ItemType Directory -Force -Path (Split-Path $pluginDst) | Out-Null

if (Test-Path $pluginDst) {
  Remove-Item -Recurse -Force $pluginDst
}

if (-not $Copy) {
  try {
    New-Item -ItemType Junction -Path $pluginDst -Target $pluginSrc | Out-Null
    Write-Host "Junction: $pluginDst -> $pluginSrc"
  } catch {
    Write-Warning "Junction failed, falling back to copy: $_"
    $Copy = $true
  }
}
if ($Copy) {
  Copy-Item -Recurse $pluginSrc $pluginDst
  Copy-Item -Recurse (Join-Path $repoRoot "ui") (Join-Path $pluginDst "ui")
  Write-Host "Copied to $pluginDst"
}

# プラグイン有効化フラグをQGIS設定に書き込む(初回のみ必要な手動作業を自動化)
$iniPath = Join-Path $QgisProfileRoot "QGIS\QGIS3.ini"
New-Item -ItemType Directory -Force -Path (Split-Path $iniPath) | Out-Null
if (-not (Test-Path $iniPath)) { New-Item -ItemType File -Path $iniPath | Out-Null }
$ini = Get-Content $iniPath -Raw -ErrorAction SilentlyContinue
if ($ini -match "\[PythonPlugins\]") {
  if ($ini -notmatch "webengine_plugin") {
    $ini = $ini -replace "\[PythonPlugins\]", "[PythonPlugins]`nwebengine_plugin=true"
    Set-Content $iniPath $ini -NoNewline
  }
} else {
  Add-Content $iniPath "`n[PythonPlugins]`nwebengine_plugin=true"
}
Write-Host "Plugin enabled in $iniPath"
Write-Host "Done. Restart QGIS if it is running."
