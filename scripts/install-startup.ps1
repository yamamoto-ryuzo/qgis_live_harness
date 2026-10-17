# 開発用: QGIS起動時にプラグインダイアログを自動で開く startup.py を
# プロファイルの python/ ディレクトリに配置する。
# 無効化したい場合は -Remove で削除。

param(
  [string]$QgisUserRoot = "$env:APPDATA\QGIS\QGIS4",
  [string]$Profile,
  [switch]$Remove
)

$ErrorActionPreference = "Stop"

if (-not $Profile) {
  $profilesIni = Join-Path $QgisUserRoot "profiles\profiles.ini"
  $Profile = (Select-String -Path $profilesIni -Pattern "lastProfile=(.+)").Matches.Groups[1].Value.Trim()
  if (-not $Profile) { $Profile = "default" }
}
$QgisProfileRoot = Join-Path $QgisUserRoot "profiles\$Profile"
$startupDir = Join-Path $QgisProfileRoot "python"
$startupPy = Join-Path $startupDir "startup.py"

if ($Remove) {
  Remove-Item $startupPy -Force -ErrorAction SilentlyContinue
  Write-Host "Removed $startupPy"
  exit 0
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$openScript = Join-Path $repoRoot "scripts\open_plugin_dialog.py"

New-Item -ItemType Directory -Force -Path $startupDir | Out-Null
@"
import runpy
runpy.run_path(r"$openScript")
"@ | Set-Content $startupPy -Encoding UTF8
Write-Host "Installed $startupPy -> $openScript"
