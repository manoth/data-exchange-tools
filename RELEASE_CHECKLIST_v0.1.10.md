# คู่มือ Pull, Build Windows และเผยแพร่ Data Exchange Tools v0.1.10

## 1. Pull และ Build

```powershell
cd "C:\path\to\data-exchange-tools"
git status --short
git switch main
git fetch origin --prune
git pull --ff-only origin main
Select-String -Path .\main.py -Pattern 'APP_VERSION'
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\build_release_0_1_10.ps1
```

ต้องได้ `APP_VERSION = "0.1.10"` และไฟล์ Release ครบ 3 ไฟล์

## 2. Smoke test launcher และตำแหน่งติดตั้ง

1. วาง EXE ในโฟลเดอร์ที่มีชื่อภาษาไทยและดับเบิลคลิก ต้องไม่เกิด `cp874/charmap` error
2. ทดสอบเปิด EXE จาก Desktop, Downloads และ USB หรือโฟลเดอร์อื่น
3. ตรวจว่ามี `%LOCALAPPDATA%\Programs\DataExchangeTools\DataExchangeTools.exe`
4. ตรวจว่า config และ update อยู่ใน `%LOCALAPPDATA%\DataExchangeTools` ไม่อยู่ข้าง EXE ต้นทาง
5. ปิด service ลบ EXE ต้นทาง แล้วเปิดผ่าน shortcut/service ใหม่ ต้องยังใช้งานได้
6. ดับเบิลคลิก v0.1.10 ซ้ำขณะ service รันอยู่ ต้องเปิดเฉพาะหน้าเว็บ
7. ให้ v0.1.9 รันอยู่ แล้วเปิด v0.1.10 ต้องสลับ service เป็น v0.1.10
8. ตรวจ Scheduled Task `DataExchangeToolsService` ว่าชี้ไปยัง EXE ใน `%LOCALAPPDATA%\Programs\DataExchangeTools`

## 3. Smoke test การแจ้งอัปเดต

1. ใช้ manifest ที่มี version สูงกว่า แล้ว login ด้วย admin ต้องพบ alert
2. กด "ไว้ภายหลัง" แล้ว refresh ต้องแจ้งอีกครั้ง
3. ติ๊ก "ไม่ต้องแจ้งเตือนเวอร์ชันนี้อีก" แล้ว refresh ต้องไม่แจ้งเวอร์ชันนั้น
4. เปลี่ยน manifest เป็น version ถัดไป ต้องกลับมาแจ้งตามปกติ
5. กด "อัปเดตตอนนี้" แล้วตรวจว่า frontend reload หรือ EXE restart ตามชนิด update

หาก Smoke test ข้อใดไม่ผ่าน ห้ามสร้าง tag หรือ Publish Release

## 4. SHA256, Tag และ Release

```powershell
$Manifest = Get-Content ".\release\latest.json" -Raw | ConvertFrom-Json
$ActualHash = (Get-FileHash ".\release\DataExchangeTools.exe" -Algorithm SHA256).Hash.ToLower()
$ActualHash -eq $Manifest.windows_exe_sha256.ToLower()
git status --short
git fetch origin --prune --tags
git tag -a v0.1.10 -m "Data Exchange Tools v0.1.10"
git push origin v0.1.10
```

สร้าง GitHub Release `Data Exchange Tools v0.1.10` โดยใช้ `RELEASE_NOTES_v0.1.10.md` และแนบ `DataExchangeTools.exe`, `DataExchangeTools-v0.1.10.exe`, `latest.json`
