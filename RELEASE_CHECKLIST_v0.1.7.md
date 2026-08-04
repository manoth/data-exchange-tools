# คู่มือ Pull, Build Windows และเผยแพร่ Data Exchange Tools v0.1.7

## 1. Pull source บน Windows

```powershell
cd "C:\path\to\data-exchange-tools"
git status --short
git switch main
git fetch origin --prune
git pull --ff-only origin main
git log -1 --oneline
Select-String -Path .\main.py -Pattern 'APP_VERSION'
```

ต้องพบ `APP_VERSION = "0.1.7"` ถ้า repository เดิมมีไฟล์แก้ค้างและไม่ทราบที่มา ห้ามใช้ `git reset --hard` ให้ clone ในโฟลเดอร์ใหม่แทน

## 2. Build EXE

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\build_release_0_1_7.ps1
```

สคริปต์จะตรวจอัตโนมัติว่า `static/index.html` ถูกฝังใน EXE แล้ว และต้องได้ไฟล์:

```text
release\DataExchangeTools.exe
release\DataExchangeTools-v0.1.7.exe
release\latest.json
```

## 3. ตรวจ SHA256

```powershell
$Manifest = Get-Content ".\release\latest.json" -Raw | ConvertFrom-Json
$ActualHash = (Get-FileHash ".\release\DataExchangeTools.exe" -Algorithm SHA256).Hash.ToLower()
$Manifest.version
$ActualHash -eq $Manifest.windows_exe_sha256.ToLower()
```

ต้องได้ version `0.1.7` และ `True`

## 4. Smoke test

- ดับเบิลคลิก `release\DataExchangeTools.exe`
- ต้องเห็นหน้า Login จริง และต้องไม่พบข้อความ `กรุณาสร้างไฟล์ static/index.html`
- Footer และ Settings แสดง `v0.1.7`
- Login และเชื่อมต่อ HIS ได้
- อัปโหลด แปลงข้อมูล และดาวน์โหลด Excel ทำงาน
- ตรวจสถานะการเสียชีวิตและรายงาน `ตายแล้วมารับบริการ` ทำงาน
- ปิดและเปิด Agent ใหม่แล้ว config และ Agent API key ไม่หาย

หาก Smoke test ไม่ผ่าน ห้ามสร้าง tag หรือ Publish Release

## 5. สร้าง tag หลัง Smoke test

```powershell
git status --short
git fetch origin --prune --tags
git rev-parse HEAD
git rev-parse origin/main
git tag -a v0.1.7 -m "Data Exchange Tools v0.1.7"
git push origin v0.1.7
```

## 6. สร้าง GitHub Release

- Tag: `v0.1.7`
- Title: `Data Exchange Tools v0.1.7`
- Description: คัดลอกจาก `RELEASE_NOTES_v0.1.7.md`
- แนบ `release\DataExchangeTools.exe`, `release\DataExchangeTools-v0.1.7.exe` และ `release\latest.json`
- ตั้งเป็น Latest และไม่เลือก Pre-release

หลัง Publish ให้ทดสอบ Auto Update จาก v0.1.6 และตรวจว่า config/API key เดิมยังอยู่ครบ
