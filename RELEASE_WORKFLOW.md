# คู่มือประจำ: การ Release Data Exchange Tools Agent

เอกสารนี้เป็นข้อตกลงการทำงานถาวรสำหรับทุกครั้งที่ผู้ใช้แจ้งว่าให้ช่วยทำ **Release เป็น version ใหม่** เช่น `v0.1.3`, `v0.2.0` หรือรุ่นถัดไป

## ขอบเขตสำคัญ

- Repository ที่ push สำหรับการ Release นี้คือ **Agent ตัวเดียว**: `manoth/data-exchange-tools`
- ห้ามนำ `server/api` หรือ Control ไปรวม commit/push ใน repository ของ Agent
- ถ้ามีการแก้ `server/api` หรือ Agent รุ่นใหม่ต้องพึ่ง API Center ที่เปลี่ยนแปลง ต้องแจ้งผู้ใช้ทุกครั้ง พร้อมระบุไฟล์และขั้นตอนอัปเดตหลังบ้านแยกต่างหาก
- ผู้ใช้เป็นผู้ build Windows EXE, สร้าง tag และสร้าง GitHub Release ด้วยตนเอง
- Codex ต้องให้คำสั่งและข้อความ Release ที่พร้อมคัดลอกทุกครั้ง

## Workflow ที่ Codex ต้องทำทุกครั้ง

เมื่อ source ของ version ใหม่ผ่าน release checks และอยู่ในสถานะพร้อมนำไป Build แล้ว Codex ต้อง stage เฉพาะไฟล์ในขอบเขต Release และ commit ให้เรียบร้อยในรอบเดียวกัน ไม่ปล่อยงานพร้อม Build ค้างแบบยังไม่ commit ส่วนการ push, tag และ Publish GitHub Release ให้ทำตามคำสั่งและลำดับความปลอดภัยด้านล่าง

เมื่อผู้ใช้ขอ Release version ใหม่ Codex ต้องดำเนินการตามลำดับต่อไปนี้

### 1. ตรวจสถานะ Agent repository

- ตรวจ branch, remote, tag ล่าสุด และไฟล์ที่ยังไม่ได้ commit
- ตรวจว่าไฟล์ลับและข้อมูลผู้ป่วยไม่ถูกนำขึ้น GitHub
- ตรวจ `.gitignore` อย่างน้อยสำหรับ:
  - `config.json`, `agent.json`, `admin.json`
  - `.key`, `.jwt_secret`, `.env`
  - `uploads/`, `release/`, `dist/`, `build/`
  - `*.xlsx`, `*.sql`, `*.7z`, `*.exe`, `*.zip`
- ห้ามลบหรือ reset งานที่ยังไม่ได้ commit โดยไม่ได้รับอนุญาต

### 2. เตรียม source สำหรับ version ใหม่

- เปลี่ยน `APP_VERSION` ใน backend และ transform
- เปลี่ยน version ที่ footer หน้าเว็บ
- เปลี่ยน query string/cache-busting ของ CSS และ JavaScript
- อัปเดต README ให้ระบุ version ปัจจุบัน
- สร้าง `RELEASE_NOTES_vX.Y.Z.md`
- สร้าง `RELEASE_CHECKLIST_vX.Y.Z.md`
- สร้าง `scripts/build_release_X_Y_Z.ps1`
- หลัง build ต้องตรวจภายใน EXE ว่ามี `static/index.html` ก่อนสร้างไฟล์ Release
- ตรวจว่าสคริปต์ PowerShell เป็น ASCII เพื่อรองรับ Windows PowerShell 5.1
- อัปเดตหรือเพิ่ม release consistency check ให้ตรงกับ version ใหม่
- ลบเฉพาะไฟล์ทดลองที่ยืนยันแล้วว่าไม่ถูกใช้งานและไม่ควรถูก bundle ใน EXE

### 3. ตรวจสอบก่อน push Agent

Codex ต้องตรวจอย่างน้อย:

- Python syntax/compile
- Unit tests ที่มีอยู่
- JavaScript syntax
- Dependency consistency
- `git diff --check`
- เลข version ในทุกตำแหน่ง
- Agent และ Control ยังเปิดหน้าเว็บได้
- API Center production และ endpoint ที่ Agent รุ่นใหม่ต้องใช้

ถ้าไม่สามารถ build `.exe` บนเครื่องปัจจุบันได้ ต้องระบุชัดเจนว่า Windows เป็นผู้ build และห้ามกล่าวว่า EXE ผ่านการทดสอบแล้ว

### 4. ให้คำสั่ง push เฉพาะ Agent

หลังตรวจสอบ source แล้ว Codex ต้องให้คำสั่งประมาณนี้ โดยเปลี่ยน version ให้ตรงกับรุ่นจริง:

```bash
cd "/Users/manoth/Desktop/Data Exchange Tools/agent"
git status --short
git add -A
git status --short
git diff --cached --check
git commit -m "release: prepare agent vX.Y.Z"
git push origin main
```

ก่อน commit ต้องเตือนผู้ใช้ให้ตรวจว่าไม่มีไฟล์ลับ ข้อมูลผู้ป่วย ฐานข้อมูล และไฟล์ผลลัพธ์อยู่ใน staging

ถ้ามี fix หลังจาก commit เตรียม Release ต้องให้ commit แยก เช่น:

```bash
git add <ไฟล์ที่แก้>
git commit -m "fix: ..."
git push origin main
```

## Workflow ฝั่ง Windows ที่ Codex ต้องสอนทุกครั้ง

### 5. Windows ดึง source ล่าสุด

ถ้ามี repository เดิมและ `git status --short` สะอาด ให้ใช้ `git pull` ไม่ต้อง clone ใหม่:

```powershell
cd "C:\path\to\data-exchange-tools"
git status --short
git switch main
git fetch origin --prune
git pull --ff-only origin main
git log -1 --oneline
```

ตรวจ version:

```powershell
Select-String -Path .\main.py -Pattern 'APP_VERSION'
```

ถ้า repository เดิมมีไฟล์แก้ค้าง ห้ามแนะนำ `git reset --hard` ให้ clone ใหม่ในโฟลเดอร์ build แยก:

```powershell
New-Item -ItemType Directory -Force "C:\Build"
cd "C:\Build"
git clone --branch main --single-branch https://github.com/manoth/data-exchange-tools.git DataExchangeTools-vX.Y.Z
cd "C:\Build\DataExchangeTools-vX.Y.Z"
```

### 6. Windows build EXE

ให้รันสคริปต์ประจำ version:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\build_release_X_Y_Z.ps1
```

ต้องได้ไฟล์ครบ:

```text
release\DataExchangeTools.exe
release\DataExchangeTools-vX.Y.Z.exe
release\latest.json
```

สคริปต์ต้องรัน `scripts\check_exe_bundle.py` และหยุด build ทันทีถ้าไม่พบ `static/index.html` ภายใน EXE

Codex ต้องสอนตรวจ `latest.json` และ SHA256:

```powershell
$Manifest = Get-Content ".\release\latest.json" -Raw | ConvertFrom-Json
$ActualHash = (Get-FileHash ".\release\DataExchangeTools.exe" -Algorithm SHA256).Hash.ToLower()
$ExpectedHash = $Manifest.windows_exe_sha256.ToLower()
$ActualHash -eq $ExpectedHash
```

ผลต้องเป็น `True`

### 7. Smoke test Windows EXE

ก่อนสร้าง tag ต้องให้ผู้ใช้ทดสอบอย่างน้อย:

- หน้าเว็บเปิดที่ `http://localhost:8899`
- Footer/Settings แสดง version ใหม่
- เชื่อมต่อฐาน HIS และ Login ได้
- อัปโหลด แปลงข้อมูล ดาวน์โหลด Excel และประวัติทำงาน
- ตรวจสอบสถานะการเสียชีวิตทำงาน
- ตรวจสอบคุณภาพข้อมูลทำงาน
- ปิดและเปิด Agent ใหม่ได้
- ไม่ทำข้อมูลตั้งค่าเดิม, Agent API key หรือไฟล์ผู้ใช้หาย

แนะนำให้ไฟล์ที่ติดตั้งจริงใช้ชื่อคงที่ `DataExchangeTools.exe` เพราะ Auto Update จะเขียนทับ EXE ตาม path เดิม หากใช้ชื่อระบุรุ่น เนื้อหาโปรแกรมจะอัปเดตแต่ชื่อไฟล์อาจยังเป็น version เก่า

## Tag และ GitHub Release ที่ Codex ต้องสอนทุกครั้ง

### 8. สร้าง tag หลัง Smoke test ผ่าน

ก่อนสร้าง tag ต้องตรวจว่า working tree สะอาด และ commit ตรงกับ source ที่ใช้ build:

```powershell
git status --short
git fetch --tags
git tag --list vX.Y.Z
```

ถ้ายังไม่มี tag:

```powershell
git tag -a vX.Y.Z -m "Data Exchange Tools vX.Y.Z"
git push origin vX.Y.Z
```

ถ้า `git fetch --tags` พบ tag อยู่บน GitHub แล้ว ห้ามสร้างหรือ push ซ้ำ ให้ตรวจว่า tag ชี้ commit ถูกต้อง:

```powershell
git show --no-patch --decorate vX.Y.Z
git rev-parse "vX.Y.Z^{}"
git rev-parse origin/main
```

### 9. สร้าง New Release บน GitHub ด้วยมือ

Codex ต้องให้ link:

```text
https://github.com/manoth/data-exchange-tools/releases/new
```

และสอนกำหนด:

- Tag: `vX.Y.Z`
- Target: `main`
- Title: `Data Exchange Tools vX.Y.Z`
- ตั้งเป็น Latest Release
- ไม่ตั้งเป็น Pre-release เว้นแต่ผู้ใช้ระบุ
- แนะนำ Save draft และตรวจสอบก่อน Publish

Codex ต้องสร้างข้อความ Release ภาษาไทยที่พร้อมคัดลอก โดยสรุป:

- คุณสมบัติใหม่
- สิ่งที่แก้ไข
- Database/API compatibility
- ข้อควรทราบก่อนอัปเดต
- ผลกระทบต่อข้อมูลและความปลอดภัย
- วิธีอัปเดต

แนบ asset เฉพาะ:

```text
DataExchangeTools.exe
DataExchangeTools-vX.Y.Z.exe
latest.json
```

ห้ามแนบ EXE ของ version เก่าที่อาจค้างอยู่ในโฟลเดอร์ `release`

### 10. ตรวจหลัง Publish และ Auto Update

Codex ต้องให้ผู้ใช้ตรวจ URL:

```text
https://github.com/manoth/data-exchange-tools/releases/latest/download/latest.json
https://github.com/manoth/data-exchange-tools/releases/latest/download/DataExchangeTools.exe
https://github.com/manoth/data-exchange-tools/releases/download/vX.Y.Z/DataExchangeTools-vX.Y.Z.exe
```

`latest.json` ต้องระบุ version ใหม่ URL ถูกต้อง และ SHA256 ตรงกับ EXE

จากนั้นทดสอบ Auto Update ด้วย Agent version ก่อนหน้า:

1. ปิด Agent รุ่นเดิมให้ service หยุดจริง
2. เปิด `DataExchangeTools.exe` รุ่นก่อนหน้า
3. ระบบตรวจ `latest.json` ตอนเริ่ม service
4. ดาวน์โหลด EXE ใหม่และตรวจ SHA256
5. ปิด service แทนที่ EXE และ restart อัตโนมัติ
6. ตรวจ Footer/Settings ว่าเป็น version ใหม่

ถ้า Agent รุ่นเดิมรันอยู่ก่อน Release และผู้ใช้ดับเบิลคลิก EXE ซ้ำ instance ใหม่จะเพียงเปิด browser จึงต้อง restart service, restart เครื่อง หรือกดเช็ก Update ใน Settings

## ข้อความที่ Codex ต้องรายงานตอนจบทุก Release

- Version ที่เตรียม
- Commit/tag ที่ใช้
- รายการไฟล์ Release
- ผลการตรวจและผล Smoke test ที่ทราบจริง
- Agent และ Control รันอยู่หรือไม่
- API Center production พร้อมหรือไม่
- ระบุชัดว่า `server/api` ถูกแก้หรือไม่
- สิ่งที่ผู้ใช้ยังต้องทำบน Windows
- สิ่งที่ผู้ใช้ยังต้องทำบน GitHub
- วิธีทดสอบ Auto Update และวิธี rollback

## หลักการห้ามข้าม

1. Push เฉพาะ Agent repository สำหรับ Agent Release
2. Windows ต้อง pull source ล่าสุดก่อน build
3. Build และ Smoke test ต้องผ่านก่อนสร้าง tag
4. Tag ต้องชี้ commit เดียวกับ source ที่ใช้ build
5. GitHub Release ต้องมี asset ครบและตั้งเป็น Latest
6. ต้องตรวจ Auto Update จาก version ก่อนหน้า
7. ต้องแจ้งทุกครั้งหากมี `server/api` ที่ผู้ใช้ต้องอัปเดตหลังบ้านด้วยตนเอง
