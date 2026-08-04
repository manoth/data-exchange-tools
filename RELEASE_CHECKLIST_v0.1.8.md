# คู่มือ Pull, Build Windows และเผยแพร่ Data Exchange Tools v0.1.8

## 1. Pull และ Build

```powershell
cd "C:\path\to\data-exchange-tools"
git status --short
git switch main
git fetch origin --prune
git pull --ff-only origin main
Select-String -Path .\main.py -Pattern 'APP_VERSION'
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\build_release_0_1_8.ps1
```

ต้องพบ `APP_VERSION = "0.1.8"` และได้:

```text
release\DataExchangeTools.exe
release\DataExchangeTools-v0.1.8.exe
release\latest.json
```

## 2. ตรวจ SHA256

```powershell
$Manifest = Get-Content ".\release\latest.json" -Raw | ConvertFrom-Json
$ActualHash = (Get-FileHash ".\release\DataExchangeTools.exe" -Algorithm SHA256).Hash.ToLower()
$Manifest.version
$ActualHash -eq $Manifest.windows_exe_sha256.ToLower()
```

ต้องได้ `0.1.8` และ `True`

## 3. Smoke test แบบ Portable

- คัดลอก EXE เพียงไฟล์เดียวไปวางที่ Desktop
- เปิด EXE แล้วต้องเห็นหน้า Login ปกติ
- Desktop ต้องไม่มี `config.json`, `.key`, `.jwt_secret`, `agent.json`, `admin.json`, `uploads` หรือ `updates` ถูกสร้างข้าง EXE
- ตรวจว่า `%LOCALAPPDATA%\DataExchangeTools` ถูกสร้าง
- ไปที่ Settings แล้วกด `เปิดโฟลเดอร์ข้อมูลโปรแกรม` ต้องเปิดโฟลเดอร์ถูกต้อง
- ทดสอบอัปเกรดจาก v0.1.7 ที่มี config/key อยู่ข้าง EXE ค่าตั้งเดิมต้องถูกคัดลอกไปใช้งานต่อได้
- ย้าย EXE ไปอีกโฟลเดอร์แล้วเปิดใหม่ ค่าตั้งเดิมต้องยังอยู่
- Login, HIS, upload, Excel, ตรวจการตาย และตรวจคุณภาพข้อมูลทำงาน

หาก Smoke test ไม่ผ่าน ห้ามสร้าง tag หรือ Publish Release

## 4. Tag และ GitHub Release

```powershell
git status --short
git fetch origin --prune --tags
git rev-parse HEAD
git rev-parse origin/main
git tag -a v0.1.8 -m "Data Exchange Tools v0.1.8"
git push origin v0.1.8
```

สร้าง GitHub Release ชื่อ `Data Exchange Tools v0.1.8` โดยคัดลอกจาก `RELEASE_NOTES_v0.1.8.md` และแนบไฟล์ Release ทั้ง 3 ไฟล์
