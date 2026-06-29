# Data Exchange Tools

เว็บแอปสำหรับอัปโหลดไฟล์ Excel Exchange จาก HDC แล้วเติม `person_cid` และ `full_name` กลับจากฐานข้อมูล HosXP/HosXP PCU โดย join ด้วย `pid` กับตาราง `person` และ Login ด้วยตาราง `opduser`

## คุณสมบัติ

- ตั้งค่าฐานข้อมูลได้เฉพาะ local admin
- ปิด service ได้เฉพาะ local admin
- ตรวจสอบและรัน update script ได้เฉพาะ local admin
- local admin เริ่มต้นคือ `admin` / `admin` และบังคับเปลี่ยนรหัสผ่านครั้งแรก
- Login ด้วย `opduser.loginname` และ `opduser.passweb = MD5(password)`
- ตั้งค่าฐานข้อมูล MySQL/MariaDB ของ HosXP ผ่านหน้าเว็บ
- เข้ารหัสรหัสผ่านฐานข้อมูลด้วย Fernet ก่อนเก็บลง `config.json`
- อัปโหลดไฟล์ `.xlsx` ที่มีคอลัมน์อย่างน้อย `cid`, `pid`, `name`, `lname`, `sex`, `birth`
- คืนข้อมูลจริงจาก `person.cid` และรวม `person.pname`, `person.fname`, `person.lname` เป็น `full_name`
- แสดงผลเป็นตารางตามคอลัมน์ของไฟล์ที่อัปโหลด และ export Excel ได้
- รองรับ Windows แบบ build เป็น `.exe` และ Linux/Docker

## วิธีรันบน Windows

### แบบดับเบิลคลิกระหว่างใช้งานทั่วไป

1. ติดตั้ง Python 3.11 หรือใหม่กว่า
2. ดับเบิลคลิก `run_windows.bat`
3. Browser จะเปิดที่ `http://localhost:8899`

### Build เป็นไฟล์ exe

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe build_exe.py
```

ไฟล์จะอยู่ที่ `dist\DataExchangeTools.exe` แล้วสามารถดับเบิลคลิกเพื่อเปิดใช้งานได้

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

## การอัปเดตโปรแกรม

ระบบจะตรวจ update จากไฟล์ในโฟลเดอร์ `updates/` ที่อยู่ข้างไฟล์โปรแกรมหรือใน `DATA_DIR`

ตัวอย่าง `updates/manifest.json`

```json
{
  "version": "1.0.1",
  "script": "update.bat",
  "notes": "ปรับปรุงการแสดงผลตาราง"
}
```

บน Windows ให้วาง `update.bat` ในโฟลเดอร์เดียวกัน ส่วน Linux/Docker ใช้ `update.sh` จากนั้น login ด้วย local admin เข้าเมนูตั้งค่า กด “เช็ค Update” และกด “Update” เมื่อระบบพบเวอร์ชันใหม่กว่า

## หมายเหตุด้าน PDPA

ระบบนี้เติมข้อมูลส่วนบุคคลกลับจากฐานข้อมูลจริงของหน่วยบริการ ควรใช้งานเฉพาะในเครื่อง/เครือข่ายที่ได้รับอนุญาต และไม่ควรส่งออกไฟล์ผลลัพธ์นอกหน่วยงานโดยไม่มีฐานอำนาจหรือมาตรการคุ้มครองข้อมูลที่เหมาะสม
