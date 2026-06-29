"""
Database Connection Manager - จัดการการเชื่อมต่อฐานข้อมูล MySQL
ใช้ pymysql พร้อม context manager pattern
"""

import pymysql
import pymysql.cursors
from config import load_config


class DatabaseConnection:
    """Context manager สำหรับจัดการ connection ฐานข้อมูล"""

    def __init__(self):
        self.connection = None

    def __enter__(self):
        self.connection = get_connection()
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            try:
                if exc_type is None:
                    self.connection.commit()
                else:
                    self.connection.rollback()
            finally:
                self.connection.close()
                self.connection = None
        return False


def get_connection():
    """สร้างและส่งคืน connection ไปยังฐานข้อมูล MySQL"""
    config = load_config()

    if not config.get("host") or not config.get("database"):
        raise Exception("ยังไม่ได้ตั้งค่าฐานข้อมูล กรุณาตั้งค่าก่อนใช้งาน")

    try:
        connection = pymysql.connect(
            host=config.get("host", "localhost"),
            port=int(config.get("port", 3306)),
            database=config.get("database", ""),
            user=config.get("username", ""),
            password=config.get("password", ""),
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10,
            read_timeout=30,
            write_timeout=30
        )
        return connection
    except pymysql.err.OperationalError as e:
        error_code = e.args[0] if e.args else 0
        if error_code == 1045:
            raise Exception("ชื่อผู้ใช้หรือรหัสผ่านฐานข้อมูลไม่ถูกต้อง")
        elif error_code == 2003:
            raise Exception(f"ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ฐานข้อมูลได้ กรุณาตรวจสอบการตั้งค่า")
        elif error_code == 1049:
            raise Exception(f"ไม่พบฐานข้อมูลที่ระบุ")
        else:
            raise Exception(f"เกิดข้อผิดพลาดในการเชื่อมต่อฐานข้อมูล: {e}")
    except Exception as e:
        raise Exception(f"เกิดข้อผิดพลาดที่ไม่คาดคิด: {e}")


def execute_query(sql: str, params: tuple = None) -> int:
    """
    รัน SQL query ที่ไม่ต้องการผลลัพธ์ (INSERT, UPDATE, DELETE)
    คืนค่าจำนวนแถวที่ได้รับผลกระทบ
    """
    connection = None
    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            affected_rows = cursor.execute(sql, params)
            connection.commit()
            return affected_rows
    except Exception as e:
        if connection:
            try:
                connection.rollback()
            except Exception:
                pass
        raise Exception(f"เกิดข้อผิดพลาดในการรัน query: {e}")
    finally:
        if connection:
            try:
                connection.close()
            except Exception:
                pass


def fetch_all(sql: str, params: tuple = None) -> list:
    """
    รัน SQL query และคืนค่าผลลัพธ์ทั้งหมด
    คืนค่า list ของ dict
    """
    connection = None
    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            results = cursor.fetchall()
            return results if results else []
    except Exception as e:
        raise Exception(f"เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")
    finally:
        if connection:
            try:
                connection.close()
            except Exception:
                pass


def fetch_one(sql: str, params: tuple = None) -> dict:
    """
    รัน SQL query และคืนค่าผลลัพธ์แถวแรก
    คืนค่า dict หรือ None
    """
    connection = None
    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            result = cursor.fetchone()
            return result
    except Exception as e:
        raise Exception(f"เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")
    finally:
        if connection:
            try:
                connection.close()
            except Exception:
                pass
