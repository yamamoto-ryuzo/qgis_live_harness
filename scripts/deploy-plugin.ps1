# プラグインをQGISのプラグインディレクトリへ配置する。
# 既定ではジャンクション(管理者権限不要)を張り、失敗した場合はコピーする。
# 現在使用中のプロファイル(profiles.ini の lastProfile)を自動検出し、
# プラグイン有効化フラグ([PythonPlugins] webengine_plugin=true)をQGIS設定に書き込む。

param(
  [string]$QgisUserRoot = "$env:APPDATA\QGIS\QGIS4",
  [string]$Profile,
  [switch]$Copy
)

$ErrorActionPreference = "Stop"

# 使用中プロファイルを自動検出
if (-not $Profile) {
  $profilesIni = Join-Path $QgisUserRoot "profiles\profiles.ini"
  $Profile = (Select-String -Path $profilesIni -Pattern "lastProfile=(.+)").Matches.Groups[1].Value.Trim()
  if (-not $Profile) { $Profile = "default" }
}
$profileRoot = Join-Path $QgisUserRoot "profiles\$Profile"
Write-Host "Profile: $Profile ($profileRoot)"

$repoRoot = Split-Path -Parent $PSScriptRoot
$pluginSrc = Join-Path $repoRoot "webengine_plugin"
$pluginDst = Join-Path $profileRoot "python\plugins\webengine_plugin"

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

# プラグイン有効化フラグをQGIS設定に書き込む
# QGIS4はQGIS4.ini、QGIS3はQGIS3.ini。存在する方を使い、無ければQGIS4.iniを作成
$qgisConfDir = Join-Path $profileRoot "QGIS"
$iniPath = Join-Path $qgisConfDir "QGIS4.ini"
if (-not (Test-Path $iniPath) -and (Test-Path (Join-Path $qgisConfDir "QGIS3.ini"))) {
  $iniPath = Join-Path $qgisConfDir "QGIS3.ini"
}
New-Item -ItemType Directory -Force -Path $qgisConfDir | Out-Null
if (-not (Test-Path $iniPath)) { New-Item -ItemType File -Path $iniPath | Out-Null }

$ini = Get-Content $iniPath -Raw -ErrorAction SilentlyContinue
if ($ini -match "webengine_plugin") {
  # 既存エントリをtrueに揃える
  $ini = $ini -replace "webengine_plugin=\w+", "webengine_plugin=true"
  Set-Content $iniPath $ini -NoNewline
} elseif ($ini -match "\[PythonPlugins\]") {
  $ini = $ini -replace "\[PythonPlugins\]", "[PythonPlugins]`nwebengine_plugin=true"
  Set-Content $iniPath $ini -NoNewline
} else {
  Add-Content $iniPath "`n[PythonPlugins]`nwebengine_plugin=true"
}
Write-Host "Plugin enabled in $iniPath"
Write-Host "Done. Restart QGIS if it is running."
