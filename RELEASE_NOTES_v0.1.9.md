# Data Exchange Tools v0.1.9

เวอร์ชันนี้ปรับการเปิดโปรแกรมบน Windows ให้เป็นแบบ launcher + service เดียวกับโปรแกรม gateway client โดยป้องกันหลายเวอร์ชันเปิด server แข่งกัน

## พฤติกรรมใหม่

- ถ้ายังไม่มี service: EXE จะติดตั้งตัว service ไว้ที่ `%LOCALAPPDATA%\Programs\DataExchangeTools\DataExchangeTools.exe`, เปิด service และเปิดหน้าเว็บ
- ถ้า service เวอร์ชันเดียวกันหรือใหม่กว่ารันอยู่: EXE จะเปิดเฉพาะหน้าเว็บแล้วปิด launcher
- ถ้า EXE ที่ดับเบิลคลิกใหม่กว่า service: launcher จะหยุดรุ่นเดิม, แทนที่ service ด้วยรุ่นใหม่, เปิด service ใหม่ และจึงเปิดหน้าเว็บ
- ถ้านำ EXE รุ่นเก่ามาเปิด ระบบจะไม่ downgrade service ที่ใหม่กว่า
- ถ้า port 8899 ถูกใช้โดยโปรแกรมอื่น launcher จะแจ้งเตือนและไม่ปิด process นั้น

## ความปลอดภัยและการดูแล

- การสั่งปิด service แบบนุ่มนวลจำกัดเฉพา loopback และต้องมี launcher token ที่เก็บใน `%LOCALAPPDATA%\DataExchangeTools`
- สำหรับรุ่นเดิมที่ยังไม่มี runtime endpoint launcher จะตรวจยืนยันชื่อโปรแกรมและเวอร์ชันก่อนสั่งปิด process
- ค่าตั้งและไฟล์ทำงานยังเก็บที่ `%LOCALAPPDATA%\DataExchangeTools` ตาม v0.1.8
- Scheduled Task จะชี้ไปที่ EXE ตัว service ในตำแหน่งกลาง

## ไฟล์สำหรับ GitHub Release

- `DataExchangeTools.exe`
- `DataExchangeTools-v0.1.9.exe`
- `latest.json`
