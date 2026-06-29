"""
Authentication Module - ระบบยืนยันตัวตน
ใช้ JWT token สำหรับ authentication
"""

from datetime import datetime, timedelta
from jose import JWTError, jwt
from database import fetch_one
from config import get_jwt_secret

# JWT Configuration
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 8


def authenticate_user(username: str, password: str) -> dict:
    """
    ตรวจสอบข้อมูลผู้ใช้จากตาราง opduser
    คืนค่า dict ข้อมูลผู้ใช้เมื่อสำเร็จ, None เมื่อล้มเหลว
    """
    try:
        sql = """
            SELECT loginname, name, entryposition, doctorcode
            FROM opduser
            WHERE loginname = %s
            AND passweb = MD5(%s)
            AND (account_disable IS NULL OR account_disable = '' OR account_disable = 'N')
        """
        user = fetch_one(sql, (username, password))

        if user:
            return {
                "loginname": user.get("loginname", ""),
                "name": user.get("name", ""),
                "position": user.get("entryposition", ""),
                "doctorcode": user.get("doctorcode", "")
            }
        return None
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการตรวจสอบผู้ใช้: {e}")
        return None


def create_token(user_data: dict) -> str:
    """
    สร้าง JWT token จากข้อมูลผู้ใช้
    token หมดอายุภายใน 8 ชั่วโมง
    """
    try:
        expire = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
        payload = {
            "sub": user_data.get("loginname", ""),
            "name": user_data.get("name", ""),
            "position": user_data.get("position", ""),
            "doctorcode": user_data.get("doctorcode", ""),
            "role": user_data.get("role", "user"),
            "must_change_password": bool(user_data.get("must_change_password", False)),
            "exp": expire
        }
        secret_key = get_jwt_secret()
        token = jwt.encode(payload, secret_key, algorithm=ALGORITHM)
        return token
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการสร้าง token: {e}")
        return ""


def verify_token(token: str) -> dict:
    """
    ตรวจสอบและถอดรหัส JWT token
    คืนค่า dict ข้อมูลผู้ใช้เมื่อสำเร็จ, None เมื่อล้มเหลว
    """
    try:
        secret_key = get_jwt_secret()
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        return {
            "loginname": payload.get("sub", ""),
            "name": payload.get("name", ""),
            "position": payload.get("position", ""),
            "doctorcode": payload.get("doctorcode", ""),
            "role": payload.get("role", "user"),
            "must_change_password": bool(payload.get("must_change_password", False)),
        }
    except JWTError as e:
        print(f"Token ไม่ถูกต้องหรือหมดอายุ: {e}")
        return None
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการตรวจสอบ token: {e}")
        return None
