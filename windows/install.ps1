# Requires Windows PowerShell 5.1+, native Python 3.11 x64 launcher, internet for PyPI.
# Extract this package to C:\cad-mcp-2019 before running. No administrator needed.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Expected = 'C:\cad-mcp-2019'
if ($Root.TrimEnd('\') -ine $Expected.TrimEnd('\')) {
    throw "Extract ZIP to $Expected first. Current location: $Root"
}
if (-not (Get-Command py.exe -ErrorAction SilentlyContinue)) {
    throw 'Python launcher py.exe not found. Install Windows Python 3.11 (64-bit) first.'
}
Write-Host '[1/4] Checking Windows Python 3.11 (x64)...'
& py.exe -3.11 --version
if ($LASTEXITCODE -ne 0) { throw 'Requires Python 3.11 x64. Check: py -0p' }
$Venv = Join-Path $Root '.venv'
$Python = Join-Path $Venv 'Scripts\python.exe'
if (-not (Test-Path $Python)) {
    Write-Host '[2/4] Creating isolated Windows venv...'
    & py.exe -3.11 -m venv $Venv
    if ($LASTEXITCODE -ne 0) { throw 'venv creation failed' }
} else {
    Write-Host '[2/4] Using existing isolated Windows venv.'
}
Write-Host '[3/4] Installing PINNED U-C4N AutoCAD MCP v1.8.0 with COM extra...'
& $Python -m pip install --disable-pip-version-check 'autocad-mcp-pro[com]==1.8.0'
if ($LASTEXITCODE -ne 0) { throw 'PyPI install failed; do not proceed.' }
& $Python -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Python environment has dependency conflicts.' }
& $Python "$PSScriptRoot\check_install.py"
if ($LASTEXITCODE -ne 0) { throw 'Entry point / installed version validation failed.' }
$Work = Join-Path $Root 'work'
New-Item -ItemType Directory -Force -Path $Work | Out-Null
$Mode = Join-Path $Root 'mode.txt'
if (-not (Test-Path $Mode)) {
    [System.IO.File]::WriteAllText($Mode, "readonly`n", (New-Object System.Text.UTF8Encoding($false)))
}
$ExistingMode = (Get-Content $Mode -Raw).Trim().ToLowerInvariant()
if ($ExistingMode -notin @('readonly','sandbox')) { throw "Invalid mode.txt content: $ExistingMode" }
Write-Host '[4/4] Installed. The default mode is:' $ExistingMode
Write-Host 'Next: start AutoCAD 2019 full edition and open a DWG, then:'
Write-Host "  & '$Python' '$PSScriptRoot\verify_com.py'"
Write-Host 'Then follow README.md for test DWG generation and WSL2/Codex registration.'
