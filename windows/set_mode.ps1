# Changes permissions applied at NEXT MCP server start. Restart Codex after using.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('readonly', 'sandbox')]
    [string]$Mode
)
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$ModeFile = Join-Path $Root 'mode.txt'
if ($Mode -eq 'sandbox') {
    $Copy = Join-Path $Root 'work\ai_demo_working.dwg'
    if (-not (Test-Path $Copy)) {
        throw "Sandbox DWG not found: $Copy. Run create_demo.py first."
    }
}
[System.IO.File]::WriteAllText($ModeFile, "$Mode`n", (New-Object System.Text.UTF8Encoding($false)))
Write-Host "Mode set to: $Mode. Completely exit and restart Codex for the change to take effect."
Write-Host 'sandbox: startup guard checks the active DWG, but cannot prevent tab-switching later.'
