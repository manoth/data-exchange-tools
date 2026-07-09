$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectDir

Write-Host "Preparing Data Exchange Tools v0.1.1" -ForegroundColor Cyan

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3 -m venv .venv
}

$Python = Join-Path $ProjectDir ".venv\Scripts\python.exe"

& $Python -m pip install --upgrade pip
& $Python -m pip install --upgrade -r requirements.txt
& $Python build_exe.py

if (-not (Test-Path "dist\DataExchangeTools.exe")) {
    throw "Build failed: dist\DataExchangeTools.exe was not created."
}

& $Python make_exe_update.py `
    --version 0.1.1 `
    --exe "dist\DataExchangeTools.exe" `
    --notes "เพิ่มการจับคู่ PID ก่อน CID, ตรวจ CID 9 หลักร่วมกับเพศ วันเกิด ชื่อและนามสกุล และปรับการเทียบฐานคนตายกลาง"

Write-Host ""
Write-Host "Release assets are ready in the release folder:" -ForegroundColor Green
Write-Host "  release\DataExchangeTools.exe"
Write-Host "  release\DataExchangeTools-v0.1.1.exe"
Write-Host "  release\latest.json"
Write-Host ""
Write-Host "Upload DataExchangeTools.exe and latest.json to GitHub Release v0.1.1."
