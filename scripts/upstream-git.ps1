# upstream同期用の git 呼び出しヘルパー。
# upstreamリポジトリの同期基盤はすべて `.upstream/`(gitignore済み・
# マシンローカル)内に置き、C:\devin 直下にclone/junctionは置かない。
#
# 2つの形式を透過的に扱う:
#   .upstream/<repo>/      → 通常clone(git -C で操作)。
#     repo内にプラグインsubfolderを持つupstream(geo_report/geo_import)用。
#     subfolderは qgis-plugin/<id> へのjunctionに置き換えてある
#   .upstream/<repo>.git   → 分離gitdir(git --git-dir で操作)。
#     「repoルート=プラグイン」構造でsubfolder junctionが張れないupstream
#     (QGIS-legendView/QGIS-exportExcel)用。core.worktree=qgis-plugin/<id>
#     設定済みで、Harness側のファイルがそのままworktreeになる
#
# 使い方:
#   scripts\upstream-git.ps1 <repo名> <git引数...>
#   npm run upstream -- QGIS-legendView status
#   npm run upstream -- geo_report log --oneline -3
#   npm run upstream -- QGIS-exportExcel push
param(
  [Parameter(Mandatory = $true)][string]$Name,
  [Parameter(ValueFromRemainingArguments = $true)][string[]]$GitArgs
)

$repoRoot = Split-Path -Parent $PSScriptRoot
$cloneDir = Join-Path $repoRoot ".upstream\$Name"
$gitdir = Join-Path $repoRoot ".upstream\$Name.git"
if (Test-Path $cloneDir) {
  & git -C $cloneDir @GitArgs
} elseif (Test-Path $gitdir) {
  & git "--git-dir=$gitdir" @GitArgs
} else {
  Write-Error "upstream not found: $cloneDir or $gitdir"
  exit 1
}
exit $LASTEXITCODE
