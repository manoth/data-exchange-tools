# Data Exchange Tools v0.1.8

เวอร์ชันนี้ปรับการใช้งานบน Windows ให้เป็น Portable EXE ไฟล์เดียว ผู้ใช้สามารถวาง EXE ไว้บน Desktop หรือโฟลเดอร์ใดก็ได้ โดยไฟล์ทำงานจะไม่กระจายอยู่ข้าง EXE

## สิ่งที่เพิ่ม

- เก็บ config, encryption key, JWT secret, Agent API key, uploads, updates และ log ไว้ที่ `%LOCALAPPDATA%\DataExchangeTools`
- ไม่สร้างไฟล์ตั้งค่าข้าง EXE อีก จึงไม่ทำให้ Desktop รก
- ยังรองรับ environment variable `DATA_DIR` สำหรับหน่วยงานที่ต้องกำหนดที่เก็บเอง
- เมื่อเปิด v0.1.8 ครั้งแรก ระบบจะคัดลอก config และ key จากข้าง EXE รุ่นเดิมไปยังที่ใหม่อัตโนมัติ
- การย้ายจะไม่ลบไฟล์เดิม และไม่เขียนทับไฟล์ที่มีอยู่ในที่ใหม่
- เพิ่มส่วน `ที่เก็บข้อมูลโปรแกรม` ในหน้า Settings เพื่อแสดง path และเปิดโฟลเดอร์ด้วยปุ่มเดียว

## ความเข้ากันได้

- คงความสามารถทั้งหมดจาก v0.1.7
- Auto Update ยังอัปเดต EXE ตาม path ที่ผู้ใช้วางไว้
- Windows Startup task และ Desktop shortcut ยังทำงานตามเดิม

## ไฟล์สำหรับ GitHub Release

- `DataExchangeTools.exe`
- `DataExchangeTools-v0.1.8.exe`
- `latest.json`
