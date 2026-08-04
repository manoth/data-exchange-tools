# คู่มือ Pull, Build Windows และเผยแพร่ Data Exchange Tools v0.1.6

## 1. Pull source บน Windows

ถ้า repository เดิมสะอาด:

```powershell
cd "C:\path\to\data-exchange-tools"
git status --short
git switch main
git fetch origin --prune
git pull --ff-only origin main
git log -1 --oneline
Select-String -Path .\main.py -Pattern 'APP_VERSION'
```

ต้องพบ `APP_VERSION = "0.1.6"` หากมีไฟล์แก้ค้างและไม่ทราบที่มา ห้ามใช้ `git reset --hard` ให้ clone ในโฟลเดอร์ใหม่:

```powershell
New-Item -ItemType Directory -Force "C:\Build"
cd "C:\Build"
git clone --branch main --single-branch https://github.com/manoth/data-exchange-tools.git DataExchangeTools-v0.1.6
cd "C:\Build\DataExchangeTools-v0.1.6"
```

## 2. Build EXE

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\build_release_0_1_6.ps1
```

ต้องได้:

```text
release\DataExchangeTools.exe
release\DataExchangeTools-v0.1.6.exe
release\latest.json
```

## 3. ตรวจ SHA256

```powershell
$Manifest = Get-Content ".\release\latest.json" -Raw | ConvertFrom-Json
$ActualHash = (Get-FileHash ".\release\DataExchangeTools.exe" -Algorithm SHA256).Hash.ToLower()
$ExpectedHash = $Manifest.windows_exe_sha256.ToLower()
$Manifest.version
$ActualHash -eq $ExpectedHash
```

ต้องได้ version `0.1.6` และค่า `True`

## 4. Smoke test

- Footer และ Settings แสดง `v0.1.6`
- Login, เชื่อม HIS, อัปโหลด แปลงข้อมูล และ Excel ทำงาน
- ตรวจสถานะการเสียชีวิตและรายงาน `ตายแล้วมารับบริการ` ทำงาน
- ทดสอบบนเครือข่ายที่เคย timeout โดยกดตรวจข้อมูลใหม่
- ถ้าเครือข่ายปกติ ผลตรวจต้องสำเร็จ; ถ้ายังเชื่อมไม่ได้ ข้อความต้องแนะนำ health endpoint และ Firewall/Proxy
- ตรวจเครือข่ายเพิ่มเติมด้วย:

```powershell
Test-NetConnection apicpho.moph.go.th -Port 443
curl.exe --connect-timeout 10 https://apicpho.moph.go.th/api/health
```

- ปิดและเปิด Agent ใหม่แล้ว config และ Agent API key ต้องไม่หาย

หาก Smoke test ไม่ผ่าน ห้ามสร้าง tag หรือ Publish Release

## 5. สร้าง tag หลัง Smoke test

```powershell
git status --short
git fetch origin --prune --tags
git rev-parse HEAD
git rev-parse origin/main
git tag --list v0.1.6
git tag -a v0.1.6 -m "Data Exchange Tools v0.1.6"
git push origin v0.1.6
```

`HEAD` ต้องตรงกับ `origin/main` และ tag ต้องชี้ commit ที่ใช้ Build

## 6. สร้าง GitHub Release

เปิด `https://github.com/manoth/data-exchange-tools/releases/new`

- Tag: `v0.1.6`
- Target: commit เดียวกับที่ใช้ Build
- Title: `Data Exchange Tools v0.1.6`
- Description: คัดลอกจาก `RELEASE_NOTES_v0.1.6.md`
- ตั้งเป็น Latest และไม่เลือก Pre-release

แนบเฉพาะ:

```text
release\DataExchangeTools.exe
release\DataExchangeTools-v0.1.6.exe
release\latest.json
```

## 7. ตรวจหลัง Publish และ Rollback

ตรวจ URL:

```text
https://github.com/manoth/data-exchange-tools/releases/latest/download/latest.json
https://github.com/manoth/data-exchange-tools/releases/latest/download/DataExchangeTools.exe
https://github.com/manoth/data-exchange-tools/releases/download/v0.1.6/DataExchangeTools-v0.1.6.exe
```

ทดสอบ Auto Update จาก v0.1.5 และตรวจว่า config/API key เดิมยังอยู่ หากต้อง rollback ให้หยุด Agent แล้วนำ `DataExchangeTools.exe` รุ่นก่อนหน้าที่สำรองไว้กลับมาใช้
