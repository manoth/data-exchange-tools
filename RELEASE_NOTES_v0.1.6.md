# Data Exchange Tools v0.1.6

เวอร์ชันนี้ปรับความทนทานของการเชื่อมต่อ API Center สำหรับหน่วยบริการที่เครือข่ายช้า ไม่เสถียร หรือต้องผ่าน Firewall/Proxy โดยต่อยอดคุณสมบัติทั้งหมดจาก v0.1.5

## สิ่งที่แก้ไข

### การเทียบข้อมูลการตายส่วนกลาง

- ลดจำนวน CID ที่ส่งต่อ request จาก 1,000 เหลือ 250 รายการต่อชุด เพื่อลดขนาด request และเวลาประมวลผลผ่านเครือข่ายหน่วยบริการ
- เพิ่ม timeout ของการเทียบข้อมูลการตายจาก 15 เป็น 45 วินาทีต่อครั้ง
- retry อัตโนมัติสูงสุด 3 ครั้งเมื่อเกิด timeout, connection error, HTTP 429 หรือ HTTP 5xx
- หน่วงเวลาระหว่าง retry เพื่อลดการยิงซ้ำทันทีเมื่อเครือข่ายหรือ API กำลังฟื้นตัว
- หยุดหลังชุดแรกเมื่อยืนยันว่าเชื่อมต่อไม่ได้ แทนการรอ timeout ซ้ำครบทุกชุด CID
- refresh Agent API key อัตโนมัติหนึ่งครั้งเมื่อ API ตอบ 401 หรือ 403
- ปรับข้อความผิดพลาดให้ระบุ endpoint health และแนวทางตรวจ Firewall/Proxy โดยไม่แสดงข้อความเทคนิค `urlopen error` แก่ผู้ใช้

### การตั้งค่าขั้นสูง

ผู้ดูแลสามารถปรับผ่าน environment variables ได้เมื่อจำเป็น:

- `CENTRAL_DEATH_LOOKUP_BATCH_SIZE` ค่าเริ่มต้น `250` ช่วงที่อนุญาต 50–1,000
- `CENTRAL_DEATH_LOOKUP_TIMEOUT_SECONDS` ค่าเริ่มต้น `45` ช่วงที่อนุญาต 15–120 วินาที
- `CENTRAL_DEATH_LOOKUP_MAX_ATTEMPTS` ค่าเริ่มต้น `3` ช่วงที่อนุญาต 1–5 ครั้ง

## คุณสมบัติที่รวมจาก v0.1.5

- รายงาน `ตายแล้วมารับบริการ` แบบหนึ่งแถวต่อบุคคล พร้อมรายละเอียดทุก VN หลังวันที่ตาย
- วันที่ตายและรหัสสาเหตุการตาย ICD-10 ในหน้าที่เทียบข้อมูลส่วนกลาง
- Modal จัดการรหัสผ่านผู้ดูแลระบบ และบังคับ Login ใหม่เมื่อเปลี่ยนสำเร็จ

## ความปลอดภัยและข้อมูล

- ส่งเฉพาะ CID ที่ต้องการเทียบไปยัง API Center
- อ่านฐาน HIS แบบ read-only และไม่เขียนข้อมูลการตายกลับ HIS
- retry ใช้ request เดิมและไม่สร้างหรือแก้ไขข้อมูลผู้ป่วย
- config, Agent API key, Excel, SQL และข้อมูลผู้ป่วยไม่ถูกรวมใน GitHub Release

## ข้อควรทราบ

- หากเครื่องไม่สามารถออก HTTPS ไป `https://apicpho.moph.go.th` ได้เลย การเพิ่ม timeout จะไม่สามารถข้าม Firewall ได้ ต้องอนุญาต `DataExchangeTools.exe` หรือกำหนด Proxy ของหน่วยบริการ
- ทดสอบเครือข่ายบน Windows ได้ด้วย `Test-NetConnection apicpho.moph.go.th -Port 443` และ `curl.exe https://apicpho.moph.go.th/api/health`
- API Center ต้องรองรับ `matchedPersons`, `deathDate` และ `deathCauseCode` เพื่อแสดงรายละเอียดครบถ้วน

## ไฟล์สำหรับ GitHub Release

- `DataExchangeTools.exe`
- `DataExchangeTools-v0.1.6.exe`
- `latest.json`
