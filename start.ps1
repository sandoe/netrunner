$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Get-Command py -ErrorAction SilentlyContinue
if ($python) {
    & py -3 scripts/start_netrunner.py @args
    exit $LASTEXITCODE
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Error "Python 3 was not found. Install Python 3.10+ and run this again."
    exit 1
}

& python scripts/start_netrunner.py @args
exit $LASTEXITCODE
