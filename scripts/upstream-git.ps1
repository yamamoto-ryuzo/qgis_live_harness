# upstream同期用の git 呼び出しヘルパー。
# upstreamリポジトリの配置形式を吸収し、どの形式でも同じ入口で操作できる。
#
# 3つの形式を順に探す:
#   .upstream/<repo>/      → clone。repo内にプラグインsubfolderを持つ
#     upstream用。subfolderは qgis-plugin/<id> へのjunctionに置き換えてある
#   C:\devin/<repo>/       → clone(同上。geo_report/geo_importが現行)
#   .upstream/<repo>.git   → 分離gitdir(git --git-dir で操作)。
#     「repoルート=プラグイン/コンテンツ」構造でsubfolder junctionが
#     張れないupstream(QGIS-legendView/QGIS-exportExcel/kasugai_qgis)用。
#     core.worktree=qgis-plugin/<id> 設定済みで、
#     Harness側のファイルがそのままworktreeになる
#
# 使い方:
#   scripts\upstream-git.ps1 <repo名> <git引数...>
#   npm run upstream -- geo_report status
#   npm run upstream -- QGIS-legendView log --oneline -3
#   npm run upstream -- QGIS-exportExcel push
param(
  [Parameter(Mandatory = $true)][string]$Name,
  [Parameter(ValueFromRemainingArguments = $true)][string[]]$GitArgs
)

$repoRoot = Split-Path -Parent $PSScriptRoot
$localClone = Join-Path $repoRoot ".upstream\$Name"
$devClone = "C:\devin\$Name"
$gitdir = Join-Path $repoRoot ".upstream\$Name.git"
if (Test-Path $localClone) {
  & git -C $localClone @GitArgs
} elseif (Test-Path $devClone) {
  & git -C $devClone @GitArgs
} elseif (Test-Path $gitdir) {
  & git "--git-dir=$gitdir" @GitArgs
} else {
  Write-Error "upstream not found: $localClone / $devClone / $gitdir"
  exit 1
}
exit $LASTEXITCODE
