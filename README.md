# Data Exchange Tools

เว็บแอปสำหรับอัปโหลดไฟล์ Excel Exchange จาก HDC แล้วเติม `person_cid` และ `full_name` กลับจากฐานข้อมูล HosXP/HosXP PCU โดย join ด้วย `pid` กับตาราง `person` และ Login ด้วยตาราง `opduser`

## คุณสมบัติ

- ตั้งค่าฐานข้อมูลได้เฉพาะ local admin
- ปิด service ได้เฉพาะ local admin
- ตรวจสอบ online update ทุก 10 นาที และรัน update script ได้เฉพาะ local admin
- local admin เริ่มต้นคือ `admin` / `admin` และบังคับเปลี่ยนรหัสผ่านครั้งแรก
- Login ด้วย `opduser.loginname` และ `opduser.passweb = MD5(password)`
- ตั้งค่าฐานข้อมูล MySQL/MariaDB ของ HosXP ผ่านหน้าเว็บ
- รองรับ MariaDB 5.x ถึงรุ่นปัจจุบัน โดย fallback charset สำหรับฐานรุ่นเก่าอัตโนมัติ
- เข้ารหัสรหัสผ่านฐานข้อมูลด้วย Fernet ก่อนเก็บลง `config.json`
- Agent เชื่อม API Center ด้วย Agent API Key แบบ 1 เครื่องต่อ 1 key โดยเก็บ key ในเครื่องแบบเข้ารหัส และแสดงเฉพาะสถานะ/prefix ในหน้า Settings
- อัปโหลดไฟล์ `.xlsx` ที่มีคอลัมน์อย่างน้อย `cid`, `pid`, `name`, `lname`, `sex`, `birth`
- คืนข้อมูลจริงจาก `person.cid` และรวม `person.pname`, `person.fname`, `person.lname` เป็น `full_name`
- แสดงผลเป็นตารางตามคอลัมน์ของไฟล์ที่อัปโหลด และ export Excel ได้
- ตรวจสอบสถานะการเสียชีวิตจาก PERSON เทียบ API Center พร้อมค้นหา กรอง เรียง และส่งออก Excel
- ตรวจสอบคุณภาพข้อมูลจากรายงานที่ Control กำหนด โดย Agent ยอมรันเฉพาะคำสั่ง `SELECT`
- รายงาน `ตายแล้วมารับบริการ` เทียบ CID ใน PERSON กับ API การตายส่วนกลาง ใช้วันที่ตายจากส่วนกลางตรวจ OVST (แฟ้ม SERVICE) หลังวันตาย สรุปหนึ่งแถวต่อคน และเปิดดูวันรับบริการทั้งหมดได้
- ทุกหน้าที่เทียบฐานการตายส่วนกลางแสดงวันที่ตายและรหัสสาเหตุการตาย (ICD-10) จาก API รวมถึงหน้าตรวจสถานะ รายงานตายแล้วมารับบริการ ผลแปลงข้อมูล ประวัติ และไฟล์ Excel
- รองรับสถานะเผยแพร่รายงานแบบบังคับ รายงานทางเลือก เฉพาะหน่วยบริการ และปิดใช้งาน
- ผู้ใช้เลือกเปิดหรือปิดรายงานทางเลือกได้จากคลังรายงานใน Agent
- รองรับ Windows แบบ build เป็น `.exe` และ Linux/Docker

## Release ปัจจุบัน

- Version: `v0.1.6`
- รายละเอียด: [`RELEASE_NOTES_v0.1.6.md`](RELEASE_NOTES_v0.1.6.md)
- ขั้นตอน Pull, Build Windows และเผยแพร่: [`RELEASE_CHECKLIST_v0.1.6.md`](RELEASE_CHECKLIST_v0.1.6.md)
- Workflow มาตรฐานสำหรับ Release รุ่นถัดไป: [`RELEASE_WORKFLOW.md`](RELEASE_WORKFLOW.md)

## วิธีรันบน Windows

### แบบดับเบิลคลิกระหว่างใช้งานทั่วไป

1. ติดตั้ง Python 3.11 หรือใหม่กว่า
2. ดับเบิลคลิก `run_windows.bat`
3. Browser จะเปิดที่ `http://localhost:8899`

### Build เป็นไฟล์ exe

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe build_exe.py
```

ไฟล์จะอยู่ที่ `dist\DataExchangeTools.exe` แล้วสามารถดับเบิลคลิกเพื่อเปิดใช้งานได้

หลังจากผู้ใช้รัน `.exe` ครั้งแรกบน Windows:

- ระบบจะตรวจ GitHub Release/latest manifest อัตโนมัติ ถ้ามีเวอร์ชันใหม่กว่าจะ update ตาม manifest
- ระบบจะสร้าง Scheduled Task ชื่อ `DataExchangeToolsService` ให้รัน service อัตโนมัติตอนเปิดเครื่องหรือ login เข้า Windows
- Scheduled Task จะรันด้วยคำสั่ง `DataExchangeTools.exe --service` จึงไม่เปิด browser อัตโนมัติ
- ระบบจะสร้าง shortcut ชื่อ `Data Exchange Tools` บน Desktop สำหรับเปิด `http://localhost:8899` เมื่อผู้ใช้ต้องการเข้าใช้งาน
- ถ้าผู้ใช้ดับเบิลคลิก `.exe` ขณะที่ service รันอยู่แล้ว โปรแกรมจะเปิด browser ไปที่หน้าเว็บแล้วปิดตัว ไม่เปิด service ซ้ำ

## วิธีรันด้วย Docker บน Linux

```bash
docker compose up -d --build
```

เปิดเว็บที่ `http://localhost:8899`

ข้อมูล runtime จะถูกเก็บในโฟลเดอร์ `data/` ได้แก่ `config.json`, `.key`, `.jwt_secret`, และไฟล์ upload/export

## การตั้งค่าฐานข้อมูล

หน้าแรกให้ login ด้วย local admin

- ครั้งแรกใช้ `admin` / `admin`
- ระบบจะบังคับเปลี่ยนรหัสผ่านใหม่
- รหัสผ่านใหม่ต้องมีอย่างน้อย 8 ตัวอักษร และมีตัวพิมพ์เล็ก ตัวพิมพ์ใหญ่ ตัวเลข และอักขระพิเศษ
- หลังเปลี่ยนรหัสสำเร็จ ระบบจะบังคับให้ตั้งค่าฐานข้อมูล
- เมื่อตั้งค่าฐานข้อมูลสำเร็จ ระบบจะพาไปหน้าอัปโหลดไฟล์ Exchange

จากนั้นกรอก

- Host เช่น `192.168.1.100`
- Port ปกติคือ `3306`
- Database เช่น `hosxp_pcu`
- Username/Password ของ MySQL ที่มีสิทธิ์อ่าน `opduser` และ `person`

แนะนำให้สร้าง user ฐานข้อมูลแบบ read-only เฉพาะตารางที่ต้องใช้ เพื่อความปลอดภัย

## การปิด service

Login ด้วย local admin แล้วกดปุ่ม “ปิด service” บริเวณแถบด้านบน หรือเข้าเมนูตั้งค่าแล้วกด “ปิด service”

เมื่อปิดแล้วผู้ใช้ทุกคนจะเข้าเว็บไม่ได้จนกว่าจะเปิดโปรแกรมหรือ container ใหม่

## การอัปเดตโปรแกรมแบบ Online

เมื่อ service เริ่มทำงาน ระบบจะตรวจ online manifest อัตโนมัติ 1 ครั้ง ถ้าพบ `windows_exe_url` บน Windows build แบบ `.exe` ระบบจะดาวน์โหลด ตรวจ `sha256` สั่งแทนที่ไฟล์ `.exe` และ restart service เพื่อใช้เวอร์ชันใหม่ ถ้าเป็น `frontend_zip_url` จะดาวน์โหลด ตรวจ `sha256` และติดตั้งไฟล์ frontend ลงโฟลเดอร์ `static/` ให้เองทันที ผู้ใช้ refresh browser แล้วจะได้หน้าเว็บเวอร์ชันล่าสุด

หลังจากนั้นระบบยังตรวจ update จาก online manifest ทุก 10 นาทีเมื่อ admin ใช้งานอยู่ และยัง fallback ไปใช้ไฟล์ในโฟลเดอร์ `updates/` ได้ถ้าเช็ก online ไม่สำเร็จ

ถ้าหน้าเว็บขึ้นข้อความประมาณ `เช็ก online ไม่สำเร็จ ... ใช้ local manifest แทน` แปลว่าเครื่องที่รัน `.exe` โหลดไฟล์ `latest.json` จาก internet หรือ server กลางไม่ได้ ไม่ใช่ปัญหาที่ปุ่ม Update โดยตรง ให้ตรวจว่า URL เปิดได้จากเครื่อง Windows เครื่องนั้นโดยไม่ต้อง login

ค่าเริ่มต้นของ online manifest คือ

```text
https://github.com/manoth/data-exchange-tools/releases/latest/download/latest.json
```

สามารถเปลี่ยน URL ได้ด้วย environment variable:

```bash
UPDATE_MANIFEST_URL=https://your-domain.example/data-exchange-tools/latest.json
```

ถ้าไม่ต้องการให้ service auto update ตอนเริ่มรัน สามารถปิดได้ด้วย:

```bash
AUTO_UPDATE_ON_STARTUP=0
```

ตัวอย่าง `latest.json` สำหรับ GitHub Release หรือ update server

```json
{
  "version": "0.0.4",
  "notes": "ปรับปรุงหน้าเว็บและระบบอัปเดต",
  "windows_exe_url": "https://your-domain.example/data-exchange-tools/DataExchangeTools-0.0.4.exe",
  "windows_exe_sha256": "PUT_WINDOWS_EXE_SHA256_HERE",
  "linux_script_url": "https://your-domain.example/data-exchange-tools/update-1.0.1.sh",
  "linux_sha256": "PUT_LINUX_UPDATE_SH_SHA256_HERE"
}
```

ถ้าแก้เฉพาะ frontend เช่น `index.html`, `static/js/*.js`, `static/css/*.css`, หรือรูปภาพ สามารถปล่อยเป็น zip ได้โดยไม่ต้อง restart service:

```json
{
  "version": "0.0.5",
  "notes": "ปรับปรุงหน้าเว็บ",
  "frontend_zip_url": "https://your-domain.example/data-exchange-tools/frontend-0.0.5.zip",
  "frontend_zip_sha256": "PUT_FRONTEND_ZIP_SHA256_HERE"
}
```

โครงสร้าง zip รองรับไฟล์เหล่านี้:

```text
index.html
css/style.css
js/app.js
js/config.js
js/upload.js
images/logo.png
```

หรือจะ zip โดยมี root เป็น `static/` ก็ได้ เช่น `static/index.html`, `static/js/app.js`

สร้างไฟล์ frontend update อัตโนมัติ:

```bash
python make_frontend_update.py --version 0.0.6 --base-url https://your-domain.example/data-exchange-tools --notes "ปรับปรุงหน้าเว็บ"
```

จะได้ไฟล์ในโฟลเดอร์ `release/`:

```text
release/frontend-0.0.6.zip
release/latest.json
```

ให้อัปโหลดทั้งสองไฟล์ไปไว้ที่ URL เดียวกับ `--base-url` เช่น:

```text
https://your-domain.example/data-exchange-tools/frontend-0.0.6.zip
https://your-domain.example/data-exchange-tools/latest.json
```

จากเครื่อง Windows ที่รัน `.exe` ต้องเปิด URL `latest.json` ใน browser ได้โดยไม่ต้อง login ถ้าเปิดไม่ได้ ระบบในหน้าเว็บก็จะขึ้นว่าเช็ก online ไม่สำเร็จ

ถ้าใช้ GitHub Release ตามค่าเริ่มต้น ให้สร้าง Release แล้วแนบ asset ชื่อ `latest.json` และ `frontend-0.0.6.zip` โดย URL ค่าเริ่มต้นจะเรียกไฟล์นี้:

```text
https://github.com/manoth/data-exchange-tools/releases/latest/download/latest.json
```

กรณี repository หรือ release asset เป็น private เครื่อง client จะโหลดผ่าน URL นี้ไม่ได้ถ้าไม่มี token แนะนำให้ใช้ web server ภายใน, object storage, หรือ GitHub Release/public asset ที่เครื่องลูกเข้าถึงได้

ข้อกำหนดด้านความปลอดภัย:

- update URL ต้องเป็น `https`
- Windows `.exe` สามารถใช้ `windows_exe_url` และ `windows_exe_sha256` เพื่อให้โปรแกรมดาวน์โหลด exe ใหม่ แทนที่ตัวเอง และเปิดโปรแกรมใหม่อัตโนมัติ
- Frontend-only update สามารถใช้ `frontend_zip_url` และ `frontend_zip_sha256` เพื่อให้ service ที่กำลังรันอยู่เปลี่ยนหน้าเว็บได้ทันที แล้ว refresh หน้าเว็บ และจะถูกติดตั้งอัตโนมัติเมื่อ service เริ่มทำงานใหม่
- online update ต้องมี `sha256` ของ exe หรือ script ให้ตรงกับไฟล์จริง
- ระบบจะติดตั้ง frontend-only update อัตโนมัติตอนเริ่ม service และถ้าเป็น Windows `.exe` ที่มี `windows_exe_url` ระบบจะ self-update แล้ว restart ตัวเองได้ ส่วน update แบบ script ยังให้ admin กด “Update” เอง
- ถ้าใช้งาน repo แบบ private ต้องใช้ update URL ที่ client เข้าถึงได้ เช่น GitHub Release/public asset, web server ภายใน, หรือ object storage ที่กำหนดสิทธิ์ไว้

คำนวณ sha256:

```bash
shasum -a 256 update-1.0.1.sh
```

บน Windows PowerShell:

```powershell
Get-FileHash .\DataExchangeTools-0.0.4.exe -Algorithm SHA256
```

## การอัปเดตแบบ Local Fallback

ถ้าไม่ใช้ online update สามารถวางไฟล์ใน `updates/` ข้างไฟล์โปรแกรมหรือใน `DATA_DIR`

ตัวอย่าง `updates/manifest.json`

```json
{
  "version": "1.0.1",
  "script": "update.bat",
  "notes": "ปรับปรุงการแสดงผลตาราง"
}
```

บน Windows ให้วาง `update.bat` ในโฟลเดอร์เดียวกัน ส่วน Linux/Docker ใช้ `update.sh` จากนั้น login ด้วย local admin เข้าเมนูตั้งค่า กด “เช็ค Update” และกด “Update” เมื่อระบบพบเวอร์ชันใหม่กว่า

## บันทึกการเปลี่ยนแปลงระหว่างพัฒนา

- เพิ่มปุ่มจัดการรหัสผ่าน admin ในหน้า `ตั้งค่า` โดยเปิดฟอร์มใน modal, ต้องกรอกรหัสผ่านเดิมและยืนยันรหัสผ่านใหม่ และบังคับ Login ใหม่หลังเปลี่ยนสำเร็จ
- ปรับหน้า `ประวัติการแปลงข้อมูล` ให้หัวตารางอยู่กึ่งกลางทั้งหมด
- จัดข้อมูล `จำนวนแถว`, `สถานะ`, และ `ดำเนินการ` ให้อยู่กึ่งกลาง
- เปลี่ยนปุ่ม `ดูรายละเอียด` และ `ดาวน์โหลด` เป็นปุ่ม icon พร้อมคำอธิบายเมื่อ hover
- ปรับการเปิดรายละเอียดจากหน้า `ประวัติการแปลงข้อมูล` ให้ยังถือเป็นบริบทของหน้าประวัติ โดยเปลี่ยนหัวข้อเป็นรายละเอียดประวัติและมีปุ่มกลับไปหน้ารายการประวัติ
- ปรับการเข้าเมนู `อัปโหลดไฟล์ Exchange` และหลัง Login ให้ reset เป็นหน้าเริ่มต้นพร้อมช่องอัปโหลดไฟล์ทุกครั้ง
- ปรับการแสดงวันที่/เวลาในหน้า Agent ให้เป็นรูปแบบ `YYYY-MM-DD hh:mm:ss`
- เพิ่มการ์ดตัวกรองหลังแปลงข้อมูลในหน้า Agent ได้แก่ `ทั้งหมด`, `จับคู่ข้อมูลได้`, `จับคู่ข้อมูลไม่ได้`
- ถ้าไฟล์ Excel มี column `DISCHARGE` ระบบจะเพิ่มตัวกรอง `เทียบข้อมูลการตายกับส่วนกลาง` โดยเลือกแถวที่ `DISCHARGE != 1` แล้วนำ `CID` ที่เติมจาก HIS ไปเทียบกับ `PID` ในฐานข้อมูลคนตายกลางผ่าน API
- แถวที่พบว่า `DISCHARGE != 1` แต่มีข้อมูลในฐานคนตายกลาง จะถูก mark เป็นรายการที่ควรตรวจสอบ และสามารถกรองดูเฉพาะกลุ่มนี้ได้
- หน้า `ตั้งค่า` ของ Agent แสดงเส้นทาง `API Center URL`, endpoint heartbeat, endpoint เทียบฐานคนตายกลาง และรหัส Agent แบบอ่านอย่างเดียว เพื่อใช้ตรวจสอบเส้นทางเมื่อมีการเปลี่ยนแปลง

## หมายเหตุด้าน PDPA

ระบบนี้เติมข้อมูลส่วนบุคคลกลับจากฐานข้อมูลจริงของหน่วยบริการ ควรใช้งานเฉพาะในเครื่อง/เครือข่ายที่ได้รับอนุญาต และไม่ควรส่งออกไฟล์ผลลัพธ์นอกหน่วยงานโดยไม่มีฐานอำนาจหรือมาตรการคุ้มครองข้อมูลที่เหมาะสม
