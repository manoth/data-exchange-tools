$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectDir

$Version = "0.1.4"
$ReleaseNotes = "Report publication controls, optional report store, and automatic update status UI"

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

Write-Host "Running release checks..." -ForegroundColor Cyan
& $Python scripts\check_release.py --version $Version
Assert-CommandSucceeded "Release consistency checks"
& $Python -m unittest -v test_db_compat.py test_data_quality_sql.py
Assert-CommandSucceeded "Unit tests"

Write-Host "Building Windows executable..." -ForegroundColor Cyan
& $Python build_exe.py
Assert-CommandSucceeded "Build executable"

if (-not (Test-Path "dist\DataExchangeTools.exe")) {
    throw "Build failed: dist\DataExchangeTools.exe was not created."
}

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

Write-Host ""
Write-Host "Release assets are ready and SHA256 has been verified:" -ForegroundColor Green
Write-Host "  release\DataExchangeTools.exe"
Write-Host "  release\DataExchangeTools-v$Version.exe"
Write-Host "  release\latest.json"
Write-Host "  SHA256: $ActualHash"
Write-Host ""
Write-Host "Upload only these three files to GitHub Release v$Version."
