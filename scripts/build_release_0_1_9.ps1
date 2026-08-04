$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectDir

$Version = "0.1.9"
$ReleaseNotes = "Single-instance Windows launcher with automatic service install and version handoff"

Write-Host "Preparing Data Exchange Tools v$Version" -ForegroundColor Cyan

function Assert-CommandSucceeded([string]$Step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE"
    }
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3 -m venv .venv
    Assert-CommandSucceeded "Create Python virtual environment"
}

$Python = Join-Path $ProjectDir ".venv\Scripts\python.exe"

& $Python -m pip install --upgrade pip
Assert-CommandSucceeded "Upgrade pip"
& $Python -m pip install --upgrade -r requirements.txt
Assert-CommandSucceeded "Install requirements"

& $Python scripts\check_release.py --version $Version
Assert-CommandSucceeded "Release consistency checks"
& $Python -m unittest discover -p "test_*.py" -v
Assert-CommandSucceeded "Unit tests"

& $Python build_exe.py
Assert-CommandSucceeded "Build executable"

if (-not (Test-Path "dist\DataExchangeTools.exe")) {
    throw "Build failed: dist\DataExchangeTools.exe was not created."
}

& $Python scripts\check_exe_bundle.py "dist\DataExchangeTools.exe"
Assert-CommandSucceeded "Verify embedded frontend"

& $Python make_exe_update.py `
    --version $Version `
    --exe "dist\DataExchangeTools.exe" `
    --notes $ReleaseNotes
Assert-CommandSucceeded "Create update assets"

$Manifest = Get-Content "release\latest.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$ActualHash = (Get-FileHash "release\DataExchangeTools.exe" -Algorithm SHA256).Hash.ToLowerInvariant()

if ($Manifest.version -ne $Version) {
    throw "Manifest version mismatch: expected $Version, got $($Manifest.version)"
}
if ($Manifest.windows_exe_sha256.ToLowerInvariant() -ne $ActualHash) {
    throw "SHA256 mismatch between latest.json and DataExchangeTools.exe"
}

Write-Host "Release assets are ready:" -ForegroundColor Green
Write-Host "  release\DataExchangeTools.exe"
Write-Host "  release\DataExchangeTools-v$Version.exe"
Write-Host "  release\latest.json"
Write-Host "  SHA256: $ActualHash"
