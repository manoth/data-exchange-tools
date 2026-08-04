# คู่มือ Pull, Build Windows และเผยแพร่ Data Exchange Tools v0.1.9

## 1. Pull และ Build

```powershell
cd "C:\path\to\data-exchange-tools"
git status --short
git switch main
git fetch origin --prune
git pull --ff-only origin main
Select-String -Path .\main.py -Pattern 'APP_VERSION'
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\build_release_0_1_9.ps1
```

ต้องได้ `APP_VERSION = "0.1.9"` และไฟล์ Release ครบ 3 ไฟล์

## 2. Smoke test launcher/service

1. ปิด Data Exchange Tools ทุกรุ่น แล้วดับเบิลคลิก v0.1.9 ต้องเปิด service และหน้าเว็บ
2. ตรวจว่ามี `%LOCALAPPDATA%\Programs\DataExchangeTools\DataExchangeTools.exe`
3. ดับเบิลคลิก v0.1.9 ซ้ำขณะ service รันอยู่ ต้องเปิดเฉพาะหน้าเว็บ ไม่มี server ตัวที่สอง
4. ให้ v0.1.8 รันอยู่ แล้วดับเบิลคลิก v0.1.9 ต้องปิด v0.1.8, เปิด service v0.1.9 และเปิดหน้าเว็บ
5. ขณะ v0.1.9 รันอยู่ ให้ดับเบิลคลิก v0.1.8 ต้องไม่ downgrade service
6. ตรวจ Scheduled Task `DataExchangeToolsService` ว่าชี้ไปยัง EXE ใน `%LOCALAPPDATA%\Programs\DataExchangeTools`
7. รีสตาร์ต Windows แล้ว service ต้องเริ่มเองโดยไม่เปิด browser
8. Login, HIS, upload, Excel, ตรวจการตาย, ตรวจคุณภาพข้อมูล และ Settings ต้องทำงาน

หาก Smoke test ข้อใดไม่ผ่าน ห้ามสร้าง tag หรือ Publish Release

## 3. SHA256, Tag และ Release

```powershell
$Manifest = Get-Content ".\release\latest.json" -Raw | ConvertFrom-Json
$ActualHash = (Get-FileHash ".\release\DataExchangeTools.exe" -Algorithm SHA256).Hash.ToLower()
$ActualHash -eq $Manifest.windows_exe_sha256.ToLower()
git status --short
git fetch origin --prune --tags
git tag -a v0.1.9 -m "Data Exchange Tools v0.1.9"
git push origin v0.1.9
```

สร้าง GitHub Release `Data Exchange Tools v0.1.9` โดยใช้ `RELEASE_NOTES_v0.1.9.md` และแนบ `DataExchangeTools.exe`, `DataExchangeTools-v0.1.9.exe`, `latest.json`
