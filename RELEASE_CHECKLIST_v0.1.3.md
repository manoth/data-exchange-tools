# Release checklist: Data Exchange Tools v0.1.3

การ build `.exe` ต้องทำบน Windows และต้องอัปเดต API Center ก่อนเผยแพร่ Agent

## 1. อัปเดต API Center ก่อน

ไฟล์หลังบ้านที่ต้องอัปเดตรอบนี้:

```text
server/api/src/services/data-quality-report.service.ts
```

บน API Center ให้สำรองฐานข้อมูล แล้วรัน:

```bash
cd server/api
npm ci
npm run build
npm run migrate
# restart API Server/PM2 ตามวิธี deploy เดิม
curl https://apicpho.moph.go.th/api/health
```

ตรวจใน Control ว่ามีรายงานครบ 4 รายการ ได้แก่ รายงานน้ำหนัก/ส่วนสูงเดิมและรายงานข้อมูลบุคคลใหม่ 3 รายการ

## 2. Push source Agent จากเครื่องพัฒนา

ตรวจว่าไม่มีไฟล์ลับ ข้อมูลผู้ป่วย ฐานข้อมูล หรือผลลัพธ์อยู่ใน staging:

```bash
cd "/Users/manoth/Desktop/Data Exchange Tools/agent"
git status --short
git add -A
git status --short
git diff --cached --check
git commit -m "release: prepare agent v0.1.3"
git push origin main
```

ห้าม commit `config.json`, `agent.json`, `admin.json`, `.key`, `.jwt_secret`, `uploads/`, `release/`, `dist/`, `build/`, `.xlsx`, `.sql`, `.7z` หรือ `.exe`

## 3. Windows ดึง source ล่าสุด

ถ้า repository เดิมสะอาด ให้ pull ไม่ต้อง clone ใหม่:

```powershell
cd "C:\path\to\data-exchange-tools"
git status --short
git switch main
git fetch origin --prune
git pull --ff-only origin main
git log -1 --oneline
Select-String -Path .\main.py -Pattern 'APP_VERSION'
```

ต้องพบ `APP_VERSION = "0.1.3"` หาก repository เดิมมีไฟล์แก้ค้าง ให้หยุดและ clone ในโฟลเดอร์ build แยกแทน ห้ามใช้ `git reset --hard`

## 4. Build Windows EXE

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\build_release_0_1_3.ps1
```

ต้องได้ไฟล์:

```text
release\DataExchangeTools.exe
release\DataExchangeTools-v0.1.3.exe
release\latest.json
```

ตรวจ SHA256:

```powershell
$Manifest = Get-Content ".\release\latest.json" -Raw | ConvertFrom-Json
$ActualHash = (Get-FileHash ".\release\DataExchangeTools.exe" -Algorithm SHA256).Hash.ToLower()
$ExpectedHash = $Manifest.windows_exe_sha256.ToLower()
$ActualHash -eq $ExpectedHash
```

ผลต้องเป็น `True`

## 5. Smoke test ก่อน tag

- หน้าเว็บเปิดที่ `http://localhost:8899`
- Footer และ Settings แสดง `v0.1.3`
- เชื่อมต่อ HIS และ Login ได้
- อัปโหลด แปลงข้อมูล ดาวน์โหลด Excel และประวัติทำงาน
- หน้าตรวจสอบสถานะการเสียชีวิตทำงานและแสดงเพศเป็นชาย/หญิง
- รายงานคุณภาพข้อมูลทั้ง 4 รายการโหลดได้ โดยรายงานใหม่มีจำนวน 4,618 รายการในฐานตัวอย่างปัจจุบัน
- กรอบข้อมูล/ตัวกรองรายงานอยู่ใต้กรอบหลักการตรวจสอบ
- เมื่อคลิกการ์ดผิดปกติ ต้องเห็นปุ่มประเภทความผิดปกติพร้อมจำนวน และปุ่มต้องกรองข้อมูลจาก Cache ได้
- คลิกการ์ด ค้นหา เรียง และเปลี่ยนหน้าแล้วใช้ Cache ได้
- ปิดและเปิด Agent ใหม่ได้โดย config และ Agent API key เดิมไม่หาย

## 6. สร้าง tag หลัง Smoke test ผ่าน

```powershell
git status --short
git fetch --tags
git tag --list v0.1.3
git tag -a v0.1.3 -m "Data Exchange Tools v0.1.3"
git push origin v0.1.3
```

ถ้า `git tag --list` พบ `v0.1.3` แล้ว ห้ามสร้างหรือ push ซ้ำ ให้ตรวจ tag กับ `origin/main` ก่อน

## 7. สร้าง GitHub Release ด้วยมือ

เปิด `https://github.com/manoth/data-exchange-tools/releases/new`

- Tag: `v0.1.3`
- Target: `main`
- Title: `Data Exchange Tools v0.1.3`
- ตั้งเป็น Latest Release และไม่ตั้งเป็น Pre-release
- ใช้ข้อความจาก `RELEASE_NOTES_v0.1.3.md`
- แนบเฉพาะ `DataExchangeTools.exe`, `DataExchangeTools-v0.1.3.exe` และ `latest.json`

บันทึกเป็น Draft และตรวจชื่อไฟล์ version กับ SHA256 ก่อน Publish

## 8. ตรวจ Auto Update หลัง Publish

ตรวจ URL:

```text
https://github.com/manoth/data-exchange-tools/releases/latest/download/latest.json
https://github.com/manoth/data-exchange-tools/releases/latest/download/DataExchangeTools.exe
https://github.com/manoth/data-exchange-tools/releases/download/v0.1.3/DataExchangeTools-v0.1.3.exe
```

จาก Agent v0.1.2 ให้กดเช็ก Update หรือ restart service แล้วตรวจว่าอัปเดตเป็น v0.1.3 พร้อม SHA256 ผ่าน
