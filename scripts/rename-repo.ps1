# rename-repo.ps1 — rename repo dir qgis-webengine-plugin -> qgis-live-harness
# Run AFTER closing Devin/IDE (the agent process holds the workspace dir).
# If a junction already exists at the new name (alias), it is removed first.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\rename-repo.ps1
param(
    [string]$OldPath = "C:\devin\qgis-webengine-plugin",
    [string]$NewPath = "C:\devin\qgis-live-harness",
    [string]$ProfilePlugins = "$env:APPDATA\QGIS\QGIS4\profiles\geo_custom\python\plugins"
)
$ErrorActionPreference = "Stop"

# 1. stop processes that hold repo paths (QGIS, renderers, stale MCP shims)
Get-Process qgis-bin, QtWebEngineProcess -ErrorAction SilentlyContinue | Stop-Process -Force
Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -like "*qgis-webengine-plugin*"
} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep 2

# 2. drop the alias junction if present (use rmdir so the target is untouched)
if ((Test-Path $NewPath) -and (Get-Item $NewPath).LinkType -eq "Junction") {
    cmd /c rmdir "$NewPath"
    Write-Output "removed alias junction: $NewPath"
}

# 3. rename the repo directory (git history moves with it)
Rename-Item $OldPath (Split-Path -Leaf $NewPath)
Write-Output "renamed: $OldPath -> $NewPath"

# 4. recreate plugin junctions pointing at the new path
foreach ($dir in Get-ChildItem (Join-Path $NewPath "qgis-plugin") -Directory) {
    $link = Join-Path $ProfilePlugins $dir.Name
    if (Test-Path $link) {
        $item = Get-Item $link
        if ($item.LinkType -eq "Junction") { cmd /c rmdir "$link" }
        else { Remove-Item $link -Force -Recurse }
    }
    New-Item -ItemType Junction -Path $link -Target $dir.FullName | Out-Null
    Write-Output "junction: $link -> $($dir.FullName)"
}
Write-Output "done. reopen the workspace at $NewPath"
