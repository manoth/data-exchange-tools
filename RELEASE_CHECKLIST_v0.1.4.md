# Release checklist: Data Exchange Tools v0.1.4

Release นี้ต้องอัปเดต API Center และ Control ก่อนเผยแพร่ Agent จากนั้น push เฉพาะ Agent repository บน Mac และใช้ Windows pull source ไป build EXE

## 1. อัปเดต API Center ก่อน

สำรองฐานข้อมูล API Center แล้วอัปเดตไฟล์:

```text
server/api/src/db/schema.ts
server/api/src/scripts/migrate.ts
server/api/src/middlewares/auth.ts
server/api/src/services/agent.service.ts
server/api/src/services/data-quality-report.service.ts
server/api/src/routes/data-quality-reports.routes.ts
```

บนเครื่อง API Center รัน:

```bash
cd server/api
npm ci
npm run build
npm run migrate
# restart API Server/PM2 ตามวิธี deploy เดิม
curl https://apicpho.moph.go.th/api/health
```

Migration จะเพิ่มคอลัมน์ `publication_mode` และตาราง `data_quality_report_facilities`

## 2. Build และ deploy Control

ไฟล์ Control ที่เกี่ยวข้อง:

```text
server/angular/src/app/shared/models.ts
server/angular/src/app/pages/data-quality-reports/data-quality-reports.ts
server/angular/src/app/pages/data-quality-reports/data-quality-reports.html
server/angular/src/app/pages/data-quality-reports/data-quality-reports.scss
```

รัน:

```bash
cd server/angular
npm ci
npm run build
```

นำไฟล์ใน `dist/angular/browser/` ขึ้น Control server ตามวิธี deploy เดิม แล้วตรวจว่าหน้าจัดการรายงานมีสถานะเผยแพร่ครบ 4 แบบและเลือกหน่วยบริการได้

## 3. Mac: ตรวจและ push เฉพาะ Agent ขึ้น GitHub

เปิด Terminal บน Mac แล้วรัน:

```bash
cd "/Users/manoth/Desktop/Data Exchange Tools/agent"
git branch --show-current
git status --short
git diff --check
python3 scripts/check_release.py --version 0.1.4
python3 -m unittest -v test_db_compat.py test_data_quality_sql.py
```

ต้องอยู่ branch `main` และ release check/tests ต้องผ่าน จากนั้นตรวจไฟล์ที่จะ commit:

```bash
git add -A
git status --short
git diff --cached --check
git diff --cached --stat
```

ก่อน commit ต้องไม่พบไฟล์เหล่านี้ใน staging:

```text
config.json
agent.json
admin.json
.key
.jwt_secret
uploads/
release/
dist/
build/
*.xlsx
*.sql
*.7z
*.exe
```

เมื่อรายการถูกต้องแล้ว commit และ push:

```bash
git commit -m "release: prepare agent v0.1.4"
git push origin main
git log -1 --oneline
```

จด commit hash จาก `git log -1 --oneline` ไว้เทียบกับ Windows และ Tag

## 4. Windows: pull source ล่าสุด

ถ้ามี repository เดิมอยู่แล้วและไม่มีงานแก้ค้าง ไม่ต้อง clone ใหม่:

```powershell
cd "C:\Users\Administrator\Downloads\Profile\data-exchange-tools"
git status --short
git switch main
git fetch origin --prune
git pull --ff-only origin main
git log -1 --oneline
Select-String -Path .\main.py -Pattern 'APP_VERSION'
```

ต้องพบ:

```text
APP_VERSION = "0.1.4"
```

และ commit hash ต้องตรงกับที่ push จาก Mac

### ถ้า `git status --short` มีไฟล์แก้ค้าง

หยุดก่อน ห้ามใช้ `git reset --hard` ถ้าไม่แน่ใจว่าไฟล์เป็นของใคร ให้ clone ไปยังโฟลเดอร์ build ใหม่:

```powershell
New-Item -ItemType Directory -Force "C:\Build"
cd "C:\Build"
git clone --branch main --single-branch https://github.com/manoth/data-exchange-tools.git DataExchangeTools-v0.1.4
cd "C:\Build\DataExchangeTools-v0.1.4"
git log -1 --oneline
Select-String -Path .\main.py -Pattern 'APP_VERSION'
```

## 5. Windows: build EXE v0.1.4

จากโฟลเดอร์ repository ที่ pull ล่าสุดแล้ว รัน:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\build_release_0_1_4.ps1
```

สคริปต์จะติดตั้ง dependency, ตรวจ version, รัน unit tests, build EXE และสร้าง manifest ให้ ต้องได้ไฟล์:

```text
release\DataExchangeTools.exe
release\DataExchangeTools-v0.1.4.exe
release\latest.json
```

ตรวจ manifest และ SHA256 ซ้ำ:

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

ค่าของ `$Manifest.version` ต้องเป็น `0.1.4` และผลบรรทัดสุดท้ายต้องเป็น `True`

## 6. Smoke test EXE ก่อนสร้าง Tag

ใช้สำเนา config สำหรับทดสอบและเปิด:

```powershell
.\release\DataExchangeTools.exe
```

ตรวจอย่างน้อย:

- หน้าเว็บเปิดที่ `http://localhost:8899`
- Footer และ Settings แสดง `v0.1.4`
- เชื่อมต่อฐาน HIS และ Login ได้
- อัปโหลด แปลงข้อมูล ดาวน์โหลด Excel และประวัติทำงาน
- หน้าตรวจสอบสถานะการเสียชีวิตทำงาน
- หน้าตรวจสอบคุณภาพข้อมูลโหลดรายงานได้
- หน้า Settings แสดงสีเขียวว่าเป็นเวอร์ชันล่าสุดและไม่มีปุ่มเช็ก Update
- หน้า Control กำหนดสถานะเผยแพร่ได้ครบ 4 แบบ
- รายงานบังคับแสดงใน Agent และซ่อนไม่ได้
- รายงานทางเลือกอยู่ใน `คลังรายงาน` และเลือกเปิด/ปิดได้
- รายงานเฉพาะหน่วยบริการแสดงเฉพาะ Agent ที่มี `facility_code` ตรงกัน
- รายงานปิดใช้งานไม่แสดงใน Agent
- ปิดและเปิด Agent ใหม่แล้ว config และ Agent API key เดิมไม่หาย

หาก Smoke test ไม่ผ่าน ห้ามสร้าง Tag และห้าม Publish Release

## 7. ตรวจ source ก่อนสร้าง Tag

ใน Windows ตรวจว่า source ที่ build ตรงกับ `origin/main`:

```powershell
git status --short
git fetch origin --prune
git rev-parse HEAD
git rev-parse origin/main
git fetch --tags
git tag --list v0.1.4
```

- `git rev-parse HEAD` และ `git rev-parse origin/main` ต้องตรงกัน
- `git tag --list v0.1.4` ต้องยังไม่แสดงอะไร
- ไฟล์ใน `release/`, `dist/` และ `.venv/` ถูก ignore จึงไม่ควรทำให้ source dirty

## 8. สร้าง Tag และ New Release บน GitHub ด้วยมือ

เปิด:

```text
https://github.com/manoth/data-exchange-tools/releases/new
```

### สร้าง Tag จากหน้า GitHub

1. ที่ช่อง **Choose a tag** พิมพ์ `v0.1.4`
2. ถ้ายังไม่มี Tag ให้เลือก **Create new tag: v0.1.4 on publish**
3. Target branch เลือก `main`
4. ตรวจว่า commit ของ `main` ตรงกับ commit hash ที่ใช้ build บน Windows

วิธีนี้ไม่ต้อง `git push tag` จาก Windows และหลีกเลี่ยงปัญหา GitHub ไม่รับรหัสผ่านสำหรับ Git operations

### กรอกรายละเอียด Release

- Release title: `Data Exchange Tools v0.1.4`
- Description: คัดลอกทั้งหมดจาก `RELEASE_NOTES_v0.1.4.md`
- เลือก **Set as the latest release**
- ไม่เลือก **Set as a pre-release**
- แนะนำให้กด **Save draft** ก่อน แล้วตรวจทุกอย่างให้ครบ

### แนบ Assets

ลากไฟล์จาก Windows มาแนบเฉพาะ 3 ไฟล์นี้:

```text
release\DataExchangeTools.exe
release\DataExchangeTools-v0.1.4.exe
release\latest.json
```

ห้ามแนบ EXE รุ่นเก่าหรือไฟล์ config/ข้อมูลผู้ป่วย

เมื่อชื่อ Tag, Target, Title, Description และ Assets ถูกต้องแล้วจึงกด **Publish release**

### ทางเลือก: สร้าง Tag ด้วย Git CLI

ถ้า Windows ตั้งค่า GitHub authentication หรือ SSH พร้อมแล้ว สามารถใช้:

```powershell
git tag -a v0.1.4 -m "Data Exchange Tools v0.1.4"
git push origin v0.1.4
```

จากนั้นหน้า New Release ให้เลือก Tag `v0.1.4` ที่มีอยู่แล้ว ห้ามสร้างซ้ำ

## 9. ตรวจหลัง Publish

เปิดตรวจ URL:

```text
https://github.com/manoth/data-exchange-tools/releases/latest/download/latest.json
https://github.com/manoth/data-exchange-tools/releases/latest/download/DataExchangeTools.exe
https://github.com/manoth/data-exchange-tools/releases/download/v0.1.4/DataExchangeTools-v0.1.4.exe
```

ตรวจว่า `latest.json` ที่ดาวน์โหลดจาก GitHub ระบุ `version: 0.1.4`, URL ถูกต้อง และ SHA256 ตรงกับ EXE บน Windows

## 10. ทดสอบ Auto Update จาก v0.1.3

1. ใช้ `DataExchangeTools.exe` รุ่น v0.1.3 ที่ติดตั้งจริงด้วยชื่อคงที่
2. เปิด Agent และ Login ด้วย local admin
3. ระบบจะตรวจ update ตอนเริ่มโปรแกรมและทุก 10 นาที
4. เมื่อพบ v0.1.4 หน้า Settings จะแสดงปุ่ม `อัปเดตเป็น v0.1.4`
5. กดอัปเดตและรอให้ระบบดาวน์โหลด ตรวจ SHA256 แทนที่ EXE และ restart
6. เปิดหน้าเว็บใหม่และตรวจ Footer/Settings ว่าเป็น `v0.1.4`
7. ตรวจ config, Agent API key และการเชื่อมต่อ HIS ว่ายังอยู่ครบ

## 11. Rollback หากพบปัญหา

- หยุด Agent service ก่อนแทนที่ไฟล์
- นำ `DataExchangeTools.exe` รุ่น v0.1.3 ที่สำรองไว้กลับมาใช้
- ถ้าปัญหาอยู่ที่ Control ให้ deploy Angular build รุ่นก่อนหน้า
- ถ้าปัญหาอยู่ที่ API Center ให้ตรวจ migration และ log ก่อน ห้ามลบตารางใหม่ทันทีเพราะอาจมีการกำหนดหน่วยบริการแล้ว
- สามารถปิดรายงานที่มีปัญหาจาก Control ด้วยสถานะ `ปิดรายงาน ไม่ใช้งาน` โดยไม่ต้องแก้ HIS
