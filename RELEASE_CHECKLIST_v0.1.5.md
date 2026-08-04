# คู่มือ Pull, Build Windows และเผยแพร่ Data Exchange Tools v0.1.5

ทำตามลำดับนี้เพื่อให้ EXE, tag และ GitHub Release อ้างอิง source commit เดียวกัน

## 1. อัปเดต API Center ก่อน

API Center production ต้องตอบ endpoint `POST /api/agents/death-persons/lookup` ในรูปแบบที่มี:

```json
{
  "matchedPids": ["..."],
  "matchedPersons": [
    {
      "pid": "...",
      "deathDate": "2026-01-10",
      "deathCauseCode": "I64"
    }
  ]
}
```

ไฟล์ API Center ที่เกี่ยวข้องโดยตรง:

```text
src/services/death-person.service.ts
src/routes/agents.routes.ts
```

หลัง deploy ให้ build, restart service และตรวจ health ตามวิธีของ server:

```bash
cd server/api
npm ci
npm run build
# restart API Server หรือ PM2 ตามวิธี deploy เดิม
curl https://apicpho.moph.go.th/api/health
```

## 2. Windows ดึง source ล่าสุด

ถ้า repository เดิมไม่มีไฟล์แก้ค้าง:

```powershell
cd "C:\path\to\data-exchange-tools"
git status --short
git switch main
git fetch origin --prune
git pull --ff-only origin main
git log -1 --oneline
Select-String -Path .\main.py -Pattern 'APP_VERSION'
```

ต้องพบ `APP_VERSION = "0.1.5"` และจด commit hash จาก `git log -1 --oneline`

ถ้า `git status --short` มีไฟล์แก้ค้างและไม่แน่ใจว่าเป็นไฟล์ใคร ห้ามใช้ `git reset --hard` ให้ clone ในโฟลเดอร์ใหม่:

```powershell
New-Item -ItemType Directory -Force "C:\Build"
cd "C:\Build"
git clone --branch main --single-branch https://github.com/manoth/data-exchange-tools.git DataExchangeTools-v0.1.5
cd "C:\Build\DataExchangeTools-v0.1.5"
git log -1 --oneline
Select-String -Path .\main.py -Pattern 'APP_VERSION'
```

## 3. Build EXE v0.1.5

เปิด PowerShell ในโฟลเดอร์ repository แล้วรัน:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\build_release_0_1_5.ps1
```

สคริปต์จะสร้าง virtual environment เมื่อต้องใช้ ติดตั้ง dependency รัน release checks และ tests จากนั้น Build EXE และสร้าง manifest

ต้องได้ไฟล์:

```text
release\DataExchangeTools.exe
release\DataExchangeTools-v0.1.5.exe
release\latest.json
```

## 4. ตรวจ version และ SHA256

```powershell
$Manifest = Get-Content ".\release\latest.json" -Raw | ConvertFrom-Json
$Manifest.version
$Manifest.windows_exe_url
$ActualHash = (Get-FileHash ".\release\DataExchangeTools.exe" -Algorithm SHA256).Hash.ToLower()
$ExpectedHash = $Manifest.windows_exe_sha256.ToLower()
$ActualHash
$ExpectedHash
$ActualHash -eq $ExpectedHash
```

- `$Manifest.version` ต้องเป็น `0.1.5`
- บรรทัดสุดท้ายต้องเป็น `True`

## 5. Smoke test บน Windows

เปิดไฟล์ชื่อคงที่:

```powershell
.\release\DataExchangeTools.exe
```

ตรวจอย่างน้อย:

- เปิดหน้า `http://localhost:8899` และ Footer แสดง `v0.1.5`
- Login และเชื่อมต่อ HIS ได้
- หน้า Settings เปิด Modal เปลี่ยนรหัสผ่านได้; ใช้ข้อมูลทดสอบที่ปลอดภัยและไม่เปลี่ยนรหัสผ่านเครื่องจริงโดยไม่จำเป็น
- อัปโหลด แปลงข้อมูล ค้นหา แบ่งหน้า และดาวน์โหลด Excel ได้
- หน้าตรวจสอบสถานะการเสียชีวิตแสดงวันที่ตายและสาเหตุ ICD-10
- รายงาน `ตายแล้วมารับบริการ` สรุปหนึ่งแถวต่อคนและเปิดดูบริการทั้งหมดได้
- หน้าตรวจสอบคุณภาพข้อมูลเดิมยังทำงาน
- ปิดและเปิด Agent ใหม่แล้ว config และ Agent API key เดิมไม่หาย

ถ้า Smoke test ไม่ผ่าน ห้ามสร้าง tag และห้าม Publish Release

## 6. ตรวจ source ที่ใช้ Build

```powershell
git status --short
git fetch origin --prune
git rev-parse HEAD
git rev-parse origin/main
git fetch --tags
git tag --list v0.1.5
```

- `HEAD` ต้องตรงกับ `origin/main`
- `git status --short` ต้องไม่มี source file ที่แก้ค้าง
- ก่อนสร้าง tag คำสั่ง `git tag --list v0.1.5` ต้องยังไม่แสดง tag

## 7. สร้าง Tag

ถ้า Git authentication บน Windows พร้อม:

```powershell
git tag -a v0.1.5 -m "Data Exchange Tools v0.1.5"
git push origin v0.1.5
```

หรือสร้าง tag ตอน Publish ผ่านหน้า GitHub โดยเลือก target เป็น commit เดียวกับที่ใช้ Build

## 8. สร้าง GitHub Release

เปิด:

```text
https://github.com/manoth/data-exchange-tools/releases/new
```

กำหนด:

- Tag: `v0.1.5`
- Target: `main` และต้องตรงกับ commit ที่ใช้ Build
- Title: `Data Exchange Tools v0.1.5`
- Description: คัดลอกจาก `RELEASE_NOTES_v0.1.5.md`
- เลือก `Set as the latest release`
- ไม่เลือก Pre-release

แนบเฉพาะ:

```text
release\DataExchangeTools.exe
release\DataExchangeTools-v0.1.5.exe
release\latest.json
```

ห้ามแนบ config, key, Excel, SQL, log หรือข้อมูลผู้ป่วย

## 9. ตรวจหลัง Publish

เปิดตรวจ:

```text
https://github.com/manoth/data-exchange-tools/releases/latest/download/latest.json
https://github.com/manoth/data-exchange-tools/releases/latest/download/DataExchangeTools.exe
https://github.com/manoth/data-exchange-tools/releases/download/v0.1.5/DataExchangeTools-v0.1.5.exe
```

ตรวจว่า `latest.json` ระบุ version `0.1.5`, URL ถูกต้อง และ SHA256 ตรงกับ EXE บน Windows

## 10. ทดสอบ Auto Update และ Rollback

ทดสอบจาก Agent v0.1.4 โดยเปิด service ใหม่หรือรอรอบตรวจอัปเดต เมื่อพบ v0.1.5 ให้กดอัปเดตและตรวจว่าโปรแกรม restart พร้อมคง config และ Agent API key เดิม

หากต้อง rollback:

1. หยุด Agent service
2. นำ `DataExchangeTools.exe` v0.1.4 ที่สำรองไว้กลับมาแทน
3. เปิด Agent และตรวจ config/HIS connection
4. หากปัญหาเป็น API Center ให้ rollback deployment ตามระบบ server โดยไม่ลบฐานข้อมูลหรือ migration ทันที
