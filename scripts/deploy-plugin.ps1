# プラグインをQGISのプラグインディレクトリへ配置する。
# 既定ではジャンクション(管理者権限不要)を張る(=開発形態。repo優先)。
# 利用形態への切替は -Use(=退避版の復元)を明示した場合のみ(-Copyは旧名エイリアス)。
#
# モード遷移時は既存の利用版を退避/復元する:
#   dev化: deploy先が実体dir(=利用版)なら profiles/<profile>/qgis_live_parked/<id>
#          へ移してからjunctionを張る(QGISのスキャン外で完全に無効化)
#   use化(-Use): junctionを外し、退避した利用版があれば python/plugins/<id> へ
#          復帰する。退避も既存実体も無ければ未配置のまま
#          (=そのプラグインは利用されていなかった、という意味)
#   -Install: repoの現状を利用版としてインストール/更新するリリース操作。
#          junctionを外し、旧parkedは破棄して新しいcopyを配置する(UI操作のみ)
# ジャンクション失敗時に自動でコピーへは落とさない
# (静かにcopy化するとrepo変更が届かない陳腐化の原因になるためエラーとする)。
# 現在使用中のプロファイル(profiles.ini の lastProfile)を自動検出し、
# プラグイン有効化フラグ([PythonPlugins] <id>=true)をQGIS設定に書き込む。
# プラグインIDは plugin.config.json の id で決まる(deploy先ディレクトリ名)。

param(
  [string]$QgisUserRoot = "$env:APPDATA\QGIS\QGIS4",
  [string]$Profile,
  [switch]$Use,          # 利用モードへ切替(退避版の復元)
  [switch]$Copy,         # -Use の旧名エイリアス(互換のため残置)
  [switch]$Install,      # repo現状を利用版として配置(リリース)。利用モードへ遷移
  [switch]$Status        # 配置を変えず現在のモード/形態を表示するだけ
)

$ErrorActionPreference = "Stop"
if ($Copy) { $Use = $true }  # -Copy は -Use の旧名エイリアス

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

$markerPath = Join-Path $profileRoot "qgis_live_mode.json"

if ($Status) {
  # 現在モードを表示して終了。marker=deploy時の宣言、実態=配置物の形態
  $declared = "unknown (markerなし)"
  if (Test-Path $markerPath) {
    try { $declared = (Get-Content $markerPath -Raw | ConvertFrom-Json).mode } catch {}
  }
  Write-Host "Declared mode: $declared"
  $parkedRoot = Join-Path $profileRoot "qgis_live_parked"
  foreach ($pluginId in $pluginIds) {
    $dst = Join-Path $profileRoot "python\plugins\$pluginId"
    $parked = (Test-Path (Join-Path $parkedRoot $pluginId))
    $suffix = if ($parked) { "  (parked: 利用版退避中)" } else { "" }
    if (-not (Test-Path $dst)) {
      Write-Host "  $pluginId : not deployed$suffix"; continue
    }
    $item = Get-Item $dst -Force
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
      Write-Host "  $pluginId : junction (dev) -> $($item.Target -join ', ')$suffix"
    } else {
      Write-Host "  $pluginId : 実体dir (use)$suffix"
    }
  }
  exit 0
}

New-Item -ItemType Directory -Force -Path (Join-Path $profileRoot "python\plugins") | Out-Null

$parkedRoot = Join-Path $profileRoot "qgis_live_parked"

foreach ($pluginId in $pluginIds) {
  $pluginSrc = Join-Path $repoRoot "qgis-plugin\$pluginId"
  $pluginDst = Join-Path $profileRoot "python\plugins\$pluginId"
  $pluginParked = Join-Path $parkedRoot $pluginId

  if (-not $Use -and -not $Install) {
    # dev化: 実体dir(利用版)があればparkedへ退避。junctionはリンクのみ外す
    if (Test-Path $pluginDst) {
      $item = Get-Item $pluginDst -Force
      if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        $item.Delete()  # junctionリンクのみ削除(repo実体は無傷)
      } else {
        New-Item -ItemType Directory -Force -Path $parkedRoot | Out-Null
        if (Test-Path $pluginParked) {
          Remove-Item -Recurse -Force $pluginParked
        }
        Move-Item $pluginDst $pluginParked
        Write-Host "Parked (use版を退避): $pluginDst -> $pluginParked"
      }
    }
    try {
      New-Item -ItemType Junction -Path $pluginDst -Target $pluginSrc | Out-Null
      Write-Host "Junction: $pluginDst -> $pluginSrc"
      continue
    } catch {
      # 自動copyフォールバックはしない(実体配置はUI操作の deploy:use/deploy:install のみ)
      Write-Error ("Junction failed for ${pluginId}: $_ " +
        "スナップショット配置が必要なら -Install を明示して再実行すること(npm run deploy:install)")
    }
  }

  if ($Install) {
    # リリース: junctionを外し、旧parkedを破棄してrepo現状を新しい利用版として配置
    if (Test-Path $pluginDst) {
      $item = Get-Item $pluginDst -Force
      if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        $item.Delete()  # junctionリンクのみ削除(repo実体は無傷)
      } else {
        Remove-Item -Recurse -Force $pluginDst
      }
    }
    if (Test-Path $pluginParked) {
      Remove-Item -Recurse -Force $pluginParked  # 旧利用版は新版に置き換わり
      Write-Host "Parked removed (旧利用版を破棄): $pluginParked"
    }
    Copy-Item -Recurse $pluginSrc $pluginDst
    Write-Host "Installed: $pluginDst (repoの現状を利用版として配置)"
    continue
  }

  # use化(-Use): junctionを外し、退避版があれば復元。
  # 退避も既存実体も無ければ未配置のまま(そのプラグインは利用されていなかった)
  if (Test-Path $pluginDst) {
    $item = Get-Item $pluginDst -Force
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
      $item.Delete()  # junctionリンクのみ削除(repo実体は無傷)
    }
  }
  if (Test-Path $pluginParked) {
    # 既存実体dirが残っていても退避版を優先して差替える
    if (Test-Path $pluginDst) { Remove-Item -Recurse -Force $pluginDst }
    Move-Item $pluginParked $pluginDst
    Write-Host "Restored (退避版を復帰): $pluginParked -> $pluginDst"
  } elseif (Test-Path $pluginDst) {
    Write-Host "Kept (既存の利用版を維持): $pluginDst"
  } else {
    Write-Host "Skipped (parked無し・未配置のまま): $pluginId"
  }
}

# モード宣言を書き出す。dev=junction(repo優先)/use=実体配置(復元またはインストール)。
# harness側(qgis-session.mjs)は use モード中は自動deployしない
$deployMode = if ($Use -or $Install) { "use" } else { "dev" }
@{ mode = $deployMode; profile = $Profile; repo = $repoRoot;
   at = (Get-Date).ToString("o") } |
  ConvertTo-Json | Set-Content -Path $markerPath -Encoding UTF8
Write-Host "Deploy mode: $deployMode (marker: $markerPath)"

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
