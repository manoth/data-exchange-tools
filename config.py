"""
Config Manager - จัดการการตั้งค่าฐานข้อมูล
ใช้ Fernet encryption สำหรับเข้ารหัสรหัสผ่าน
"""

import os
import json
import sys
import base64
import hashlib
import hmac
import secrets
from typing import Optional, Tuple
import pymysql
from cryptography.fernet import Fernet

# กำหนด path สำหรับไฟล์ config
# When bundled with PyInstaller, keep writable files beside the .exe instead of
# inside the temporary extraction folder.
DATA_DIR = os.environ.get("DATA_DIR")
if DATA_DIR:
    APP_DIR = DATA_DIR
elif getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
KEY_FILE = os.path.join(APP_DIR, ".key")
JWT_SECRET_FILE = os.path.join(APP_DIR, ".jwt_secret")
ADMIN_FILE = os.path.join(APP_DIR, "admin.json")
AGENT_CONFIG_FILE = os.path.join(APP_DIR, "agent.json")
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin"
PBKDF2_ITERATIONS = 260000


def _get_or_create_key() -> bytes:
    """สร้างหรือโหลด Fernet key สำหรับเข้ารหัสรหัสผ่าน"""
    os.makedirs(APP_DIR, exist_ok=True)
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read()
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    return key


def _encrypt_password(password: str) -> str:
    """เข้ารหัสรหัสผ่านด้วย Fernet"""
    key = _get_or_create_key()
    f = Fernet(key)
    return f.encrypt(password.encode()).decode()


def _decrypt_password(encrypted_password: str) -> str:
    """ถอดรหัสรหัสผ่าน"""
    try:
        key = _get_or_create_key()
        f = Fernet(key)
        return f.decrypt(encrypted_password.encode()).decode()
    except Exception:
        return ""


def get_jwt_secret() -> str:
    """สร้างหรือโหลด JWT secret key"""
    os.makedirs(APP_DIR, exist_ok=True)
    if os.path.exists(JWT_SECRET_FILE):
        with open(JWT_SECRET_FILE, "r") as f:
            return f.read().strip()
    secret = Fernet.generate_key().decode()
    with open(JWT_SECRET_FILE, "w") as f:
        f.write(secret)
    return secret


def _hash_password(password: str, salt: bytes = None) -> dict:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return {
        "algorithm": "pbkdf2_sha256",
        "iterations": PBKDF2_ITERATIONS,
        "salt": base64.b64encode(salt).decode("ascii"),
        "hash": base64.b64encode(digest).decode("ascii"),
    }


def _verify_password(password: str, password_hash: dict) -> bool:
    try:
        salt = base64.b64decode(password_hash["salt"])
        expected = base64.b64decode(password_hash["hash"])
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(password_hash.get("iterations", PBKDF2_ITERATIONS)),
        )
        return hmac.compare_digest(digest, expected)
    except Exception:
        return False


def load_admin() -> dict:
    """โหลดข้อมูล local admin. ถ้ายังไม่มีให้ใช้ admin/admin และบังคับเปลี่ยนรหัส"""
    if not os.path.exists(ADMIN_FILE):
        return {
            "username": DEFAULT_ADMIN_USERNAME,
            "password_hash": _hash_password(DEFAULT_ADMIN_PASSWORD, b"default-admin-key"),
            "must_change_password": True,
        }
    try:
        with open(ADMIN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "username": DEFAULT_ADMIN_USERNAME,
            "password_hash": _hash_password(DEFAULT_ADMIN_PASSWORD, b"default-admin-key"),
            "must_change_password": True,
        }


def save_admin(admin_data: dict) -> dict:
    try:
        os.makedirs(APP_DIR, exist_ok=True)
        with open(ADMIN_FILE, "w", encoding="utf-8") as f:
            json.dump(admin_data, f, indent=2, ensure_ascii=False)
        return {"success": True, "message": "บันทึกรหัสผ่านผู้ดูแลระบบสำเร็จ"}
    except Exception as e:
        return {"success": False, "message": f"ไม่สามารถบันทึกรหัสผ่านผู้ดูแลระบบได้: {e}"}


def validate_admin_password(password: str, old_password: str = "") -> Tuple[bool, str]:
    """ตรวจความยากของรหัสผ่าน admin ตาม baseline สากล"""
    if password == old_password:
        return False, "รหัสผ่านใหม่ต้องไม่ซ้ำกับรหัสผ่านเดิม"
    if len(password) < 8:
        return False, "รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร"
    if any(ch.isspace() for ch in password):
        return False, "รหัสผ่านต้องไม่มีช่องว่าง"
    if password.lower() in {"admin", "password", "administrator"}:
        return False, "รหัสผ่านนี้เดาง่ายเกินไป"
    checks = [
        any(ch.islower() for ch in password),
        any(ch.isupper() for ch in password),
        any(ch.isdigit() for ch in password),
        any(not ch.isalnum() for ch in password),
    ]
    if not all(checks):
        return False, "รหัสผ่านต้องมีตัวพิมพ์เล็ก ตัวพิมพ์ใหญ่ ตัวเลข และอักขระพิเศษ"
    return True, ""


def authenticate_admin(username: str, password: str) -> Optional[dict]:
    admin = load_admin()
    if username != admin.get("username", DEFAULT_ADMIN_USERNAME):
        return None
    if not _verify_password(password, admin.get("password_hash", {})):
        return None
    return {
        "loginname": admin.get("username", DEFAULT_ADMIN_USERNAME),
        "name": "System Administrator",
        "position": "Admin",
        "doctorcode": "",
        "role": "admin",
        "must_change_password": bool(admin.get("must_change_password", True)),
    }


def change_admin_password(old_password: str, new_password: str) -> dict:
    admin = load_admin()
    if not _verify_password(old_password, admin.get("password_hash", {})):
        return {"success": False, "message": "รหัสผ่านเดิมไม่ถูกต้อง"}
    valid, message = validate_admin_password(new_password, old_password)
    if not valid:
        return {"success": False, "message": message}
    admin["password_hash"] = _hash_password(new_password)
    admin["must_change_password"] = False
    return save_admin(admin)


def load_config() -> dict:
    """โหลดการตั้งค่าจากไฟล์ config.json"""
    if not os.path.exists(CONFIG_FILE):
        return {
            "host": "",
            "port": 3306,
            "database": "",
            "username": "",
            "password": ""
        }
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        # ถอดรหัสรหัสผ่านก่อนส่งกลับ
        if config.get("password"):
            config["password"] = _decrypt_password(config["password"])
        return config
    except json.JSONDecodeError:
        return {
            "host": "",
            "port": 3306,
            "database": "",
            "username": "",
            "password": ""
        }
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการโหลดการตั้งค่า: {e}")
        return {
            "host": "",
            "port": 3306,
            "database": "",
            "username": "",
            "password": ""
        }


def save_config(config_data: dict) -> dict:
    """บันทึกการตั้งค่าลงไฟล์ config.json"""
    try:
        os.makedirs(APP_DIR, exist_ok=True)
        # เข้ารหัสรหัสผ่านก่อนบันทึก
        config_to_save = {
            "host": config_data.get("host", ""),
            "port": int(config_data.get("port", 3306)),
            "database": config_data.get("database", ""),
            "username": config_data.get("username", ""),
            "password": _encrypt_password(config_data.get("password", ""))
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_to_save, f, indent=2, ensure_ascii=False)
        return {"success": True, "message": "บันทึกการตั้งค่าสำเร็จ"}
    except Exception as e:
        return {"success": False, "message": f"ไม่สามารถบันทึกการตั้งค่าได้: {e}"}


def public_config() -> dict:
    """คืนค่าการตั้งค่าที่ปลอดภัยสำหรับแสดงในหน้าเว็บ โดยไม่ส่งรหัสผ่านกลับไป client"""
    config = load_config()
    return {
        "host": config.get("host", ""),
        "port": int(config.get("port", 3306) or 3306),
        "database": config.get("database", ""),
        "username": config.get("username", ""),
        "configured": is_configured(),
    }


def load_agent_config() -> dict:
    """โหลดข้อมูล Agent สำหรับเชื่อม API Center โดยถอดรหัส API key เฉพาะฝั่ง server"""
    if not os.path.exists(AGENT_CONFIG_FILE):
        return {
            "api_key": "",
            "api_key_prefix": "",
            "registered_at": "",
            "api_center_url": "",
        }
    try:
        with open(AGENT_CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        if config.get("api_key"):
            config["api_key"] = _decrypt_password(config["api_key"])
        return config
    except Exception:
        return {
            "api_key": "",
            "api_key_prefix": "",
            "registered_at": "",
            "api_center_url": "",
        }


def save_agent_api_key(api_key: str, api_key_prefix: str = "", api_center_url: str = "") -> dict:
    """บันทึก Agent API key แบบเข้ารหัส"""
    try:
        os.makedirs(APP_DIR, exist_ok=True)
        config_to_save = {
            "api_key": _encrypt_password(api_key),
            "api_key_prefix": api_key_prefix or api_key[:16],
            "registered_at": datetime_now_string(),
            "api_center_url": api_center_url,
        }
        with open(AGENT_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_to_save, f, indent=2, ensure_ascii=False)
        return {"success": True, "message": "บันทึก Agent API key สำเร็จ"}
    except Exception as e:
        return {"success": False, "message": f"ไม่สามารถบันทึก Agent API key ได้: {e}"}


def public_agent_config() -> dict:
    """คืนค่า Agent API config ที่ปลอดภัย ไม่ส่ง key จริงไปหน้าเว็บ"""
    config = load_agent_config()
    return {
        "api_key_configured": bool(config.get("api_key")),
        "api_key_prefix": config.get("api_key_prefix", ""),
        "registered_at": config.get("registered_at", ""),
        "api_center_url": config.get("api_center_url", ""),
    }


def datetime_now_string() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def test_connection(config_data: dict) -> dict:
    """ทดสอบการเชื่อมต่อฐานข้อมูล MySQL"""
    try:
        connection = pymysql.connect(
            host=config_data.get("host", "localhost"),
            port=int(config_data.get("port", 3306)),
            database=config_data.get("database", ""),
            user=config_data.get("username", ""),
            password=config_data.get("password", ""),
            charset="utf8mb4",
            connect_timeout=10
        )
        connection.close()
        return {"success": True, "message": "เชื่อมต่อฐานข้อมูลสำเร็จ"}
    except pymysql.err.OperationalError as e:
        error_code = e.args[0] if e.args else 0
        if error_code == 1045:
            return {"success": False, "message": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"}
        elif error_code == 2003:
            return {"success": False, "message": f"ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ {config_data.get('host')}:{config_data.get('port')} ได้ กรุณาตรวจสอบ host และ port"}
        elif error_code == 1049:
            return {"success": False, "message": f"ไม่พบฐานข้อมูล '{config_data.get('database')}'"}
        else:
            return {"success": False, "message": f"เกิดข้อผิดพลาดในการเชื่อมต่อ: {e}"}
    except Exception as e:
        return {"success": False, "message": f"เกิดข้อผิดพลาดที่ไม่คาดคิด: {e}"}


def is_configured() -> bool:
    """ตรวจสอบว่ามีการตั้งค่าฐานข้อมูลแล้วหรือยัง"""
    if not os.path.exists(CONFIG_FILE):
        return False
    try:
        config = load_config()
        return bool(config.get("host") and config.get("database") and config.get("username"))
    except Exception:
        return False
