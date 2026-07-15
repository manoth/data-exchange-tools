# Release checklist: Data Exchange Tools v0.1.2

เอกสารนี้เป็นขั้นตอนสำหรับผู้ดูแล repository `manoth/data-exchange-tools` โดยการ build `.exe` ต้องทำบน Windows

## 0. อัปเดต API Center และ Control ก่อนปล่อย Agent

Agent `v0.1.2` เรียก endpoint `/api/agents/data-quality-reports` จึงต้องยืนยันว่า API Center production ใช้ชุดที่มีระบบรายงานคุณภาพข้อมูล มิฉะนั้นหน้า `ตรวจสอบคุณภาพข้อมูล` จะใช้งานไม่ได้

ณ วันที่เตรียม Release endpoint production ตอบกลับและพบรายงาน `abnormal-weight-height` แล้ว แต่ source ใน `server/api` ยังมีไฟล์ที่ไม่ได้ commit จึงต้อง commit/push ให้ repository ตรงกับ production เพื่อให้ deploy ครั้งถัดไปไม่ทำฟังก์ชันนี้หาย หากไม่แน่ใจว่า production ใช้ commit เดียวกัน ให้ deploy ซ้ำตามขั้นตอนด้านล่าง

ไฟล์ API Center ที่เกี่ยวข้องใน `server/api`:

- `src/app.ts`
- `src/db/schema.ts`
- `src/routes/agents.routes.ts`
- `src/scripts/migrate.ts`
- `src/middlewares/agent-auth.ts`
- `src/routes/data-quality-reports.routes.ts`
- `src/services/data-quality-report.service.ts`

ตรวจและ commit repository API Center แยกจาก Agent:

```bash
cd server/api
npm ci
npm run build
git status --short
git add src/app.ts src/db/schema.ts src/routes/agents.routes.ts src/scripts/migrate.ts \
  src/middlewares/agent-auth.ts src/routes/data-quality-reports.routes.ts \
  src/services/data-quality-report.service.ts
git diff --cached --check
git commit -m "feat: add configurable data quality reports"
git push origin main
```

บนเครื่อง production ให้สำรองฐานข้อมูล API Center ก่อน แล้วดึง source ล่าสุดและ deploy:

```bash
git pull --ff-only origin main
./deploy-api.sh
curl https://apicpho.moph.go.th/api/health
```

`deploy-api.sh` จะรัน `npm ci`, migration, TypeScript build และ restart PM2 ให้ หลัง migration ต้องตรวจว่ามีตาราง `data_quality_reports` และมีรายงานเริ่มต้น `ตรวจสอบน้ำหนัก/ส่วนสูงผิดปกติ`

Control ต้อง build และ deploy รุ่นที่มีหน้า `/data-quality-reports` ด้วย:

```bash
cd server/angular
npm ci
npm run build
```

นำผลลัพธ์จาก `server/angular/dist/angular/` ไปแทน Control production ตามวิธี deploy เดิม แล้วทดสอบว่าเพิ่ม แก้ไข เปิด/ปิด และลบรายงานได้ ก่อนเริ่มปล่อย Agent

## 1. ตรวจ source code ก่อน commit

จากโฟลเดอร์โปรเจกต์ Agent:

```powershell
git status --short
if (-not (Test-Path ".venv\Scripts\python.exe")) { py -3 -m venv .venv }
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe scripts\check_release.py --version 0.1.2
.venv\Scripts\python.exe -m unittest -v test_db_compat.py
```

ตรวจว่าไม่มีไฟล์เหล่านี้อยู่ในรายการที่จะ commit:

- `config.json`, `agent.json`, `admin.json`
- `.key`, `.jwt_secret`
- ไฟล์ภายใน `uploads/`, `release/`, `dist/` และ `build/`
- ไฟล์ฐานข้อมูลหรือข้อมูลผู้ป่วย เช่น `.sql`, `.xlsx`, `.7z`

ไฟล์เหล่านี้ถูกกำหนดไว้ใน `.gitignore` แล้ว แต่ควรตรวจ `git status` ทุกครั้งก่อน commit

## 2. Commit และ push source code

```powershell
git add -A
git status --short
git diff --cached --check
git commit -m "release: prepare agent v0.1.2"
git push origin main
```

ก่อนสั่ง commit ให้ตรวจรายการจาก `git status --short` อีกครั้ง ถ้าพบไฟล์ลับหรือข้อมูลผู้ป่วยให้หยุดและนำออกจาก staging ก่อน

## 3. Build ไฟล์ Windows Release

เปิด PowerShell บน Windows จากโฟลเดอร์ Agent แล้วรัน:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\build_release_0_1_2.ps1
```

สคริปต์จะติดตั้ง dependency, ตรวจ version, ตรวจ Python syntax, รัน unit tests, build `.exe`, สร้าง `latest.json` และตรวจ SHA256 ให้อัตโนมัติ

ผลลัพธ์ต้องมีครบ:

```text
release\DataExchangeTools.exe
release\DataExchangeTools-v0.1.2.exe
release\latest.json
```

## 4. Smoke test บน Windows ก่อนสร้าง tag

1. สำรอง config ของ Agent เดิม และหยุด Agent รุ่นที่กำลังรัน
2. เปิด `release\DataExchangeTools-v0.1.2.exe`
3. ตรวจว่าหน้าเว็บเปิดที่ `http://localhost:8899`
4. หน้า Settings ต้องแสดง `v0.1.2`
5. ทดสอบเชื่อมต่อฐาน HIS และ login
6. ทดสอบอัปโหลดไฟล์ แปลงข้อมูล ดาวน์โหลด Excel และหน้าประวัติ
7. ทดสอบหน้า `ตรวจสอบสถานะการเสียชีวิต`
8. ทดสอบหน้า `ตรวจสอบคุณภาพข้อมูล` และรายงานน้ำหนัก/ส่วนสูงผิดปกติ
9. ปิดแล้วเปิด Agent ใหม่ เพื่อตรวจว่าการตั้งค่าและ service startup ยังทำงาน

ถ้าทดสอบไม่ผ่าน ให้แก้ source แล้วกลับไปเริ่มจากขั้น commit/build ใหม่ ห้ามใช้ tag เดิมกับ source คนละชุด

## 5. สร้างและ push tag

หลัง smoke test ผ่าน และ `main` ตรงกับ commit ที่ใช้ build:

```powershell
git status --short
git tag -a v0.1.2 -m "Data Exchange Tools v0.1.2"
git push origin v0.1.2
```

## 6. สร้าง GitHub Release

1. เปิด `https://github.com/manoth/data-exchange-tools/releases/new`
2. เลือก tag `v0.1.2`
3. Release title: `Data Exchange Tools v0.1.2`
4. คัดลอกเนื้อหาจาก `RELEASE_NOTES_v0.1.2.md` ไปใส่รายละเอียด Release
5. แนบ asset ทั้งสามไฟล์:
   - `DataExchangeTools.exe`
   - `DataExchangeTools-v0.1.2.exe`
   - `latest.json`
6. บันทึกเป็น Draft ก่อน ตรวจชื่อไฟล์และ version ใน `latest.json`
7. กด Publish release เมื่อทุกอย่างถูกต้อง

`DataExchangeTools.exe` และ `latest.json` เป็นไฟล์ที่ Auto Update ใช้ผ่าน URL `/releases/latest/download/...` จึงต้องตั้ง Release นี้เป็น Release ล่าสุดและห้ามเปลี่ยนชื่อไฟล์

## 7. ทดสอบ Auto Update หลัง Publish

จากเครื่อง Windows ที่ติดตั้งรุ่นเก่า:

1. เปิด URL `https://github.com/manoth/data-exchange-tools/releases/latest/download/latest.json` ต้องดาวน์โหลดได้โดยไม่ต้อง login
2. เปิด Agent รุ่นเก่า ไปที่ **ตั้งค่า → เช็ก Update**
3. ระบบต้องพบ `v0.1.2`, ดาวน์โหลดสำเร็จ และ SHA256 ผ่าน
4. หลัง restart หน้า Settings ต้องแสดง `v0.1.2`
5. หากทดสอบผ่านแล้วจึงแจ้งผู้ใช้งานให้อัปเดต

## Rollback

หากพบปัญหารุนแรงหลัง Publish ให้เอา Release `v0.1.2` ออกจากสถานะ Latest หรือ unpublish ชั่วคราว แล้วให้ Release รุ่นก่อนกลับมาเป็น Latest ระหว่างแก้ไข ห้ามนำไฟล์ `.exe` คนละ build มาเขียนทับ asset เดิมโดยใช้ version เดิม
