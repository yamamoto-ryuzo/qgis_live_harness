# 初回クローン後の環境セットアップスクリプト。
# 前提ツール(QGIS 4 / Node.js 24+ / Python 3.13+)を確認し、不足していれば
# winget でインストールした上で、npm install → (任意)playwright install →
# プラグイン配置(deploy:copy)まで一括実行する。
#
# 使い方(リポジトリルートで):
#   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1          # 対話あり
#   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Yes    # 全て自動承諾
#   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -CheckOnly  # 確認のみ
# または: npm run setup (Node導入済みの場合)

param(
  [switch]$Yes,            # 確認プロンプトを省略して全てインストール
  [switch]$CheckOnly,      # 確認のみ(インストール・npm install等を行わない)
  [switch]$SkipPlaywright, # npx playwright install を省略(L1テスト不要な場合)
  [switch]$SkipDeploy      # npm run deploy:copy を省略
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$issues = @()

function Confirm-Install([string]$name) {
  if ($CheckOnly) { return $false }
  if ($Yes) { return $true }
  $ans = Read-Host "$name をインストールしますか? [y/N]"
  return $ans -match "^[yY]"
}

# winget導入後など、同一セッションでPATHを更新するために再読込する
function Refresh-Path {
  $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
              [Environment]::GetEnvironmentVariable("Path", "User")
}

function Test-Winget {
  if (Get-Command winget -ErrorAction SilentlyContinue) { return $true }
  Write-Warning "winget が見つかりません。Microsoft Store の「アプリ インストーラー」を導入するか、各ツールを手動でインストールしてください。"
  return $false
}

Write-Host "=== QGIS Live Harness セットアップ ===" -ForegroundColor Cyan
Write-Host "リポジトリ: $repoRoot"
Write-Host ""

# --- 1. QGIS 4.x ------------------------------------------------------------
Write-Host "[1/4] QGIS 4.x を確認..." -ForegroundColor Cyan
$qgisExe = $env:QGIS_EXE
if (-not $qgisExe) {
  $cand = Get-ChildItem "$env:ProgramFiles\QGIS*\bin\qgis-bin.exe" -ErrorAction SilentlyContinue |
    Sort-Object FullName -Descending | Select-Object -First 1
  if ($cand) { $qgisExe = $cand.FullName }
}
if ($qgisExe -and (Test-Path $qgisExe)) {
  Write-Host "  OK: $qgisExe" -ForegroundColor Green
} else {
  Write-Warning "  QGIS が見つかりません (C:\Program Files\QGIS* / QGIS_EXE)"
  if ((Test-Winget) -and (Confirm-Install "QGIS (winget: OSGeo.QGIS)")) {
    winget install --id OSGeo.QGIS -e --accept-source-agreements --accept-package-agreements
    Refresh-Path
    $cand = Get-ChildItem "$env:ProgramFiles\QGIS*\bin\qgis-bin.exe" -ErrorAction SilentlyContinue |
      Sort-Object FullName -Descending | Select-Object -First 1
    if ($cand) { Write-Host "  OK: $($cand.FullName)" -ForegroundColor Green }
    else { $issues += "QGISのインストールを確認できませんでした" }
  } else {
    $issues += "QGIS 4.0.x 未導入 (https://qgis.org/ から入手。別の場所に導入した場合は QGIS_EXE env を設定)"
  }
}

# --- 2. Node.js 24+ ---------------------------------------------------------
Write-Host "[2/4] Node.js 24+ を確認..." -ForegroundColor Cyan
function Get-NodeMajor {
  $node = Get-Command node -ErrorAction SilentlyContinue
  if (-not $node) { return $null }
  $v = (& node --version) -replace "^v", ""
  return [int]($v.Split(".")[0])
}
$nodeMajor = Get-NodeMajor
if ($nodeMajor -and $nodeMajor -ge 24) {
  Write-Host "  OK: node v$(node --version)".Replace("vv", "v") -ForegroundColor Green
} else {
  if ($nodeMajor) { Write-Warning "  Node.js v$nodeMajor は古すぎます (24+ が必要)" }
  else { Write-Warning "  Node.js が見つかりません" }
  if ((Test-Winget) -and (Confirm-Install "Node.js LTS (winget: OpenJS.NodeJS.LTS)")) {
    winget install --id OpenJS.NodeJS.LTS -e --accept-source-agreements --accept-package-agreements
    Refresh-Path
    $nodeMajor = Get-NodeMajor
    if ($nodeMajor -and $nodeMajor -ge 24) { Write-Host "  OK: node $(node --version)" -ForegroundColor Green }
    else { $issues += "Node.js 24+ のインストールを確認できませんでした(新しいターミナルで再実行してください)" }
  } else {
    $issues += "Node.js 24+ 未導入 (https://nodejs.org/)"
  }
}

# --- 3. Python 3.13+ と pytest (ユニットテスト用・任意) ----------------------
Write-Host "[3/4] Python 3.13+ / pytest を確認 (test:unit 用・任意)..." -ForegroundColor Cyan
function Get-PythonVersion {
  $py = Get-Command python -ErrorAction SilentlyContinue
  if (-not $py) { return $null }
  $out = & python --version 2>&1
  if ($out -match "Python (\d+)\.(\d+)") { return @([int]$Matches[1], [int]$Matches[2]) }
  return $null  # Windows Store のエイリアス等
}
$pyVer = Get-PythonVersion
$pyOk = $pyVer -and ($pyVer[0] -gt 3 -or ($pyVer[0] -eq 3 -and $pyVer[1] -ge 13))
if ($pyOk) {
  Write-Host "  OK: Python $($pyVer[0]).$($pyVer[1])" -ForegroundColor Green
} else {
  if ($pyVer) { Write-Warning "  Python $($pyVer[0]).$($pyVer[1]) は古すぎます (3.13+ が必要)" }
  else { Write-Warning "  Python が見つかりません" }
  if ((Test-Winget) -and (Confirm-Install "Python 3.13 (winget: Python.Python.3.13)")) {
    winget install --id Python.Python.3.13 -e --accept-source-agreements --accept-package-agreements
    Refresh-Path
    $pyVer = Get-PythonVersion
    $pyOk = $pyVer -and ($pyVer[0] -gt 3 -or ($pyVer[0] -eq 3 -and $pyVer[1] -ge 13))
    if ($pyOk) { Write-Host "  OK: Python $($pyVer[0]).$($pyVer[1])" -ForegroundColor Green }
    else { $issues += "Python 3.13+ のインストールを確認できませんでした(新しいターミナルで再実行してください)" }
  } else {
    $issues += "Python 3.13+ 未導入 (test:unit を使う場合のみ必要。https://www.python.org/)"
  }
}
if ($pyOk) {
  & python -m pytest --version *> $null
  if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK: pytest 導入済み" -ForegroundColor Green
  } elseif (-not $CheckOnly -and ($Yes -or (Confirm-Install "pytest (pip install pytest)"))) {
    & python -m pip install pytest
  } else {
    $issues += "pytest 未導入 (test:unit を使う場合は pip install pytest)"
  }
}

# --- 4. npm install / playwright / deploy -----------------------------------
Write-Host "[4/4] リポジトリ側のセットアップ..." -ForegroundColor Cyan
if ($CheckOnly) {
  Write-Host "  (CheckOnly のためスキップ)"
} elseif (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  $issues += "npm が使えないため npm install / deploy を実行できませんでした"
} else {
  Push-Location $repoRoot
  try {
    Write-Host "  npm install ..."
    npm install
    if ($LASTEXITCODE -ne 0) { $issues += "npm install が失敗しました" }

    if (-not $SkipPlaywright) {
      Write-Host "  npx playwright install (L1テスト用ブラウザ。-SkipPlaywright で省略可) ..."
      npx playwright install
      if ($LASTEXITCODE -ne 0) { $issues += "npx playwright install が失敗しました" }
    }

    if (-not $SkipDeploy) {
      Write-Host "  npm run deploy:copy (プラグインをQGISへ配置) ..."
      npm run deploy:copy
      if ($LASTEXITCODE -ne 0) { $issues += "npm run deploy:copy が失敗しました" }
    }
  } finally {
    Pop-Location
  }
}

# --- 結果 --------------------------------------------------------------------
Write-Host ""
if ($issues.Count -eq 0) {
  Write-Host "=== セットアップ完了 ===" -ForegroundColor Green
  Write-Host "次の一歩:"
  Write-Host "  npm run live:ensure     # 常駐QGISを用意"
  Write-Host "  npm run test:live       # 実QGIS内で検証"
  Write-Host "  npm run new:plugin my_plugin  # 自分のプラグインの足場を作る"
} else {
  Write-Host "=== 未解決の項目があります ===" -ForegroundColor Yellow
  $issues | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
  Write-Host "解決後にこのスクリプトを再実行してください(導入済みの手順は再実行しても安全)。"
  exit 1
}
