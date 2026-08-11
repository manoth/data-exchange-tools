#!/usr/bin/env python3
"""
Script สำหรับ build Data Exchange Tools เป็นไฟล์ .exe สำหรับ Windows
ใช้ PyInstaller ในการ bundle ทุกอย่างเป็นไฟล์เดียว

วิธีใช้:
    1. ติดตั้ง PyInstaller: pip install pyinstaller
    2. รัน: python build_exe.py
    3. ไฟล์ .exe จะอยู่ที่: dist/DataExchangeTools.exe
"""

import os
import subprocess
import sys


def configure_standard_streams():
    """Keep build output printable on Windows runners using legacy code pages."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


def create_pyinstaller_command(base_dir):
    """Create a deterministic PyInstaller command for the application."""
    main_script = os.path.join(base_dir, 'main.py')
    static_dir = os.path.join(base_dir, 'static')
    static_index = os.path.join(static_dir, 'index.html')

    if not os.path.isfile(main_script):
        raise FileNotFoundError(f"ไม่พบไฟล์โปรแกรมหลัก: {main_script}")
    if not os.path.isfile(static_index):
        raise FileNotFoundError(f"ไม่พบไฟล์หน้าเว็บที่ต้อง bundle: {static_index}")

    # PyInstaller 6 uses SOURCE:DEST on every supported platform. Using
    # os.pathsep here produces a semicolon on Windows and can silently omit
    # the frontend from a one-file executable.
    add_data = f'--add-data={static_dir}:static'

    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
        '--onefile',
        '--name', 'DataExchangeTools',
        '--windowed',
        add_data,
        '--hidden-import=uvicorn.logging',
        '--hidden-import=uvicorn.loops',
        '--hidden-import=uvicorn.loops.auto',
        '--hidden-import=uvicorn.protocols',
        '--hidden-import=uvicorn.protocols.http',
        '--hidden-import=uvicorn.protocols.http.auto',
        '--hidden-import=uvicorn.protocols.websockets',
        '--hidden-import=uvicorn.protocols.websockets.auto',
        '--hidden-import=uvicorn.lifespan',
        '--hidden-import=uvicorn.lifespan.on',
        '--hidden-import=uvicorn.lifespan.off',
        '--hidden-import=pymysql',
        '--hidden-import=openpyxl',
        '--hidden-import=jose',
        '--hidden-import=multipart',
        '--hidden-import=cryptography',
        '--hidden-import=cryptography.fernet',
        '--hidden-import=windows_launcher',
        '--collect-all=uvicorn',
        '--collect-all=fastapi',
        '--collect-all=starlette',
    ]

    ico_path = os.path.join(static_dir, 'images', 'favicon.ico')
    if os.path.exists(ico_path):
        cmd.append(f'--icon={ico_path}')

    cmd.append(main_script)
    return cmd

def build():
    """Build the application into a single executable"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    requirements_path = os.path.join(base_dir, 'requirements.txt')

    print("📦 กำลังติดตั้ง/อัปเดต dependencies จาก requirements.txt...")
    try:
        subprocess.check_call([
            sys.executable,
            '-m',
            'pip',
            'install',
            '--upgrade',
            '-r',
            requirements_path
        ])
        print("✅ ติดตั้ง dependencies สำเร็จ")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ ติดตั้ง dependencies ไม่สำเร็จ: {e}")
        print("   แนะนำให้ลบโฟลเดอร์ .venv แล้วสร้างใหม่ด้วย Python 3.11 หรือ 3.13 จากนั้นลองอีกครั้ง")
        sys.exit(1)

    # ตรวจสอบว่า PyInstaller ติดตั้งแล้วหรือยัง
    try:
        import PyInstaller
        print("✅ พบ PyInstaller แล้ว")
    except ImportError:
        print("📦 กำลังติดตั้ง PyInstaller...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
        print("✅ ติดตั้ง PyInstaller สำเร็จ")

    try:
        cmd = create_pyinstaller_command(base_dir)
    except FileNotFoundError as exc:
        print(f"\n❌ {exc}")
        sys.exit(1)

    print("\n🔨 กำลัง build ไฟล์ .exe...")
    print(f"   คำสั่ง: {' '.join(cmd)}\n")

    # รัน PyInstaller
    try:
        subprocess.check_call(cmd, cwd=base_dir)

        exe_path = os.path.join(base_dir, 'dist', 'DataExchangeTools.exe')
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"\n✅ Build สำเร็จ!")
            print(f"   📁 ไฟล์: {exe_path}")
            print(f"   📦 ขนาด: {size_mb:.1f} MB")
            print(f"\n💡 วิธีใช้งาน:")
            print(f"   1. ดับเบิลคลิกไฟล์ DataExchangeTools.exe")
            print(f"   2. Browser จะเปิดอัตโนมัติที่ http://localhost:8899 เฉพาะตอนดับเบิลคลิก")
            print(f"   3. ระบบจะสร้าง Windows Startup task ให้รัน service ตอนเปิดเครื่องแบบไม่เปิด browser")
            print(f"   4. ระบบจะสร้าง shortcut ที่ Desktop สำหรับเปิดหน้าเว็บเมื่ออยากใช้งาน")
            print(f"   5. ตั้งค่าการเชื่อมต่อฐานข้อมูล HosXP แล้ว Login ด้วย username/password จาก HosXP")
        else:
            print("❌ ไม่พบไฟล์ .exe หลัง build")

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Build ล้มเหลว: {e}")
        print("   ลองรัน: pip install pyinstaller แล้ว build ใหม่")
        sys.exit(1)


if __name__ == '__main__':
    configure_standard_streams()
    print("=" * 50)
    print("  Data Exchange Tools - Build Script")
    print("  สร้างไฟล์ .exe สำหรับ Windows")
    print("=" * 50)
    build()
