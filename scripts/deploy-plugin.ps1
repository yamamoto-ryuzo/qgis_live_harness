# プラグインをQGISのプラグインディレクトリへ配置する。
# 既定ではジャンクション(管理者権限不要)を張り、失敗した場合はコピーする。
# 現在使用中のプロファイル(profiles.ini の lastProfile)を自動検出し、
# プラグイン有効化フラグ([PythonPlugins] <id>=true)をQGIS設定に書き込む。
# プラグインIDは plugin.config.json の id で決まる(deploy先ディレクトリ名)。

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
# qgis-plugin/ 直下で metadata.txt を持つフォルダを全てプラグインとしてdeployする。
# フォルダ名=QGISのプラグインID。複数プラグインを並行開発できる。
$pluginIds = Get-ChildItem (Join-Path $repoRoot "qgis-plugin") -Directory |
  Where-Object { Test-Path (Join-Path $_.FullName "metadata.txt") } |
  ForEach-Object { $_.Name }
if (-not $pluginIds) { Write-Error "no plugins found under qgis-plugin/" }
Write-Host "Plugins: $($pluginIds -join ', ')"

New-Item -ItemType Directory -Force -Path (Join-Path $profileRoot "python\plugins") | Out-Null

foreach ($pluginId in $pluginIds) {
  $pluginSrc = Join-Path $repoRoot "qgis-plugin\$pluginId"
  $pluginDst = Join-Path $profileRoot "python\plugins\$pluginId"

  if (Test-Path $pluginDst) {
    Remove-Item -Recurse -Force $pluginDst
  }

  if (-not $Copy) {
    try {
      New-Item -ItemType Junction -Path $pluginDst -Target $pluginSrc | Out-Null
      Write-Host "Junction: $pluginDst -> $pluginSrc"
      continue
    } catch {
      Write-Warning "Junction failed for $pluginId, falling back to copy: $_"
    }
  }
  Copy-Item -Recurse $pluginSrc $pluginDst
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
foreach ($pluginId in $pluginIds) {
  if ($ini -match "$pluginId=") {
    # 既存エントリをtrueに揃える
    $ini = $ini -replace "$pluginId=\w+", "$pluginId=true"
  } elseif ($ini -match "\[PythonPlugins\]") {
    $ini = $ini -replace "\[PythonPlugins\]", "[PythonPlugins]`n$pluginId=true"
  } else {
    $ini += "`n[PythonPlugins]`n$pluginId=true"
  }
}
Set-Content $iniPath $ini -NoNewline
Write-Host "Plugin enabled in $iniPath"
Write-Host "Done. Restart QGIS if it is running."
