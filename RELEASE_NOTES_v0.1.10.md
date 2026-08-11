# Data Exchange Tools v0.1.10

เวอร์ชันนี้ทำให้ไฟล์ EXE แบบพกพาเปิดจากตำแหน่งใดก็ได้ ติดตั้ง service ไว้ในตำแหน่งถาวร และให้ผู้ดูแลยืนยันก่อนติดตั้งอัปเดต

## การเปิดโปรแกรมและตำแหน่งจัดเก็บ

- ไฟล์ที่ผู้ใช้ดาวน์โหลดสามารถเปิดจาก Desktop, Downloads, USB หรือโฟลเดอร์อื่นได้
- launcher คัดลอก service ไปที่ `%LOCALAPPDATA%\Programs\DataExchangeTools\DataExchangeTools.exe`
- config, key, uploads, frontend override และไฟล์ update เก็บใน `%LOCALAPPDATA%\DataExchangeTools`
- EXE เป็น PyInstaller one-file จึงไม่แตกไฟล์โปรแกรมถาวรไว้ข้างไฟล์ต้นทาง
- หลังติดตั้งแล้วสามารถลบไฟล์ EXE ต้นทางได้โดย service ในตำแหน่งถาวรยังทำงานต่อ

## การแจ้งอัปเดต

- ค่าเริ่มต้นไม่ติดตั้งอัปเดตเองตอน service เริ่มทำงาน
- เมื่อ admin เข้าระบบหรือ refresh หน้าเว็บ ระบบจะแสดงกล่องถามเมื่อพบเวอร์ชันใหม่
- เลือก "ไว้ภายหลัง" เพื่อให้ถามใหม่ในการ refresh ครั้งถัดไป
- เลือก "ไม่ต้องแจ้งเตือนเวอร์ชันนี้อีก" เพื่อปิดเฉพาะเลขเวอร์ชันนั้น รุ่นถัดไปยังแจ้งตามปกติ
- องค์กรที่ต้องการ auto-install แบบเดิมยังเปิดได้ด้วย `AUTO_UPDATE_ON_STARTUP=1`

## แก้ไขข้อผิดพลาด Windows

- แก้ `UnicodeEncodeError: 'charmap' codec can't encode characters` บน Windows console รหัส cp874
- launcher ทำงานก่อนพิมพ์ข้อความ startup และตั้ง stdout/stderr เป็น UTF-8 พร้อม fallback ที่ปลอดภัย
- ตัด emoji ออกจาก service banner เพื่อรองรับ Windows console รุ่นเก่า

## ไฟล์สำหรับ GitHub Release

- `DataExchangeTools.exe`
- `DataExchangeTools-v0.1.10.exe`
- `latest.json`
