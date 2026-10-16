# PreScale installer for Windows.
#
#   irm https://prescale.dev/install.ps1 | iex
#
# Installs uv (https://docs.astral.sh/uv) if you don't have it, then
# `uv tool install prescale` from PyPI into its own isolated environment. uv
# brings its own Python if needed. Run it again to upgrade.
#
# Options (environment variables): PRESCALE_VERSION, PRESCALE_EXTRAS (e.g. mcp),
# PRESCALE_NO_MODIFY_PATH=1. Source:
# https://github.com/pyjeebz/PreScale/blob/main/landing-page/public/install.ps1

$ErrorActionPreference = "Stop"

function Find-Uv {
    $cmd = Get-Command uv -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($candidate in @("$env:USERPROFILE\.local\bin\uv.exe", "$env:USERPROFILE\.cargo\bin\uv.exe")) {
        if (Test-Path $candidate) { return $candidate }
    }
    return $null
}

$uv = Find-Uv
if (-not $uv) {
    Write-Host "-> Installing uv (manages PreScale's Python environment)"
    $env:UV_NO_MODIFY_PATH = "1"
    try {
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression | Out-Null
    } catch {
        throw "Couldn't install uv. Install it from https://docs.astral.sh/uv, or use: pip install prescale"
    }
    $uv = Find-Uv
    if (-not $uv) { throw "uv installed but wasn't found. Open a new terminal and run this again." }
}

$spec = if ($env:PRESCALE_PACKAGE) { $env:PRESCALE_PACKAGE } else { "prescale" }
if ($env:PRESCALE_EXTRAS) { $spec = "$spec[$($env:PRESCALE_EXTRAS)]" }
if ($env:PRESCALE_VERSION) { $spec = "$spec==$($env:PRESCALE_VERSION)" }

Write-Host "-> Installing $spec"
& $uv tool install --force --upgrade --quiet $spec
if ($LASTEXITCODE -ne 0) { throw "Install failed. Try again, or use: pip install prescale" }

$binDir = (& $uv tool dir --bin).Trim()
$prescale = Join-Path $binDir "prescale.exe"
if (-not (Test-Path $prescale)) { throw "Installed, but $prescale is missing." }

$onPath = ($env:PATH -split ";") -contains $binDir
if (-not $onPath -and -not $env:PRESCALE_NO_MODIFY_PATH) {
    & $uv tool update-shell | Out-Null
}

Write-Host ""
Write-Host "OK  $(& $prescale --version) installed at $prescale"
if (-not $onPath) {
    Write-Host ""
    Write-Host "    Open a new terminal so 'prescale' is on your PATH."
}
Write-Host ""
Write-Host "    Try it:   prescale run http://localhost:8000"
Write-Host "    Connect:  prescale login        (optional: send runs to your dashboard)"
Write-Host "    Upgrade:  run this installer again"
