# upstream同期用の gitdir 経由 git 呼び出し。
# 「repoルート=プラグイン」構造のupstreamリポジトリは subfolder junction が
# 張れないため、gitdir を .upstream/<repo>.git に退避し core.worktree を
# qgis-plugin/<id> に向けている(Harness側が正本)。
#
# 使い方:
#   scripts\upstream-git.ps1 <repo名> <git引数...>
#   npm run upstream -- QGIS-legendView status
#   npm run upstream -- QGIS-legendView -- commit -am "msg" → push まで同様
#
# 対象:
#   QGIS-legendView    → qgis-plugin/QGIS-legendView-main
#   QGIS-exportExcel   → qgis-plugin/export_excel
param(
  [Parameter(Mandatory = $true)][string]$Name,
  [Parameter(ValueFromRemainingArguments = $true)][string[]]$GitArgs
)

$repoRoot = Split-Path -Parent $PSScriptRoot
$gitdir = Join-Path $repoRoot ".upstream\$Name.git"
if (-not (Test-Path $gitdir)) {
  Write-Error "upstream gitdir not found: $gitdir"
  exit 1
}
& git "--git-dir=$gitdir" @GitArgs
exit $LASTEXITCODE
