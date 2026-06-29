"""
Pydantic Models - โมเดลข้อมูลสำหรับ API
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ConfigModel(BaseModel):
    """โมเดลสำหรับการตั้งค่าฐานข้อมูล"""
    host: str
    port: int = Field(default=3306)
    database: str
    username: str
    password: str


class LoginRequest(BaseModel):
    """โมเดลสำหรับ request การเข้าสู่ระบบ"""
    username: str
    password: str


class ChangeAdminPasswordRequest(BaseModel):
    """โมเดลสำหรับเปลี่ยนรหัสผ่าน admin"""
    old_password: str
    new_password: str


class LoginResponse(BaseModel):
    """โมเดลสำหรับ response การเข้าสู่ระบบ"""
    success: bool
    token: str = ""
    user: Dict[str, str] = Field(default_factory=dict)


class TransformRequest(BaseModel):
    """โมเดลสำหรับ request การแปลงข้อมูล"""
    file_id: str


class UploadResponse(BaseModel):
    """โมเดลสำหรับ response การอัพโหลดไฟล์"""
    file_id: str
    preview: List[Dict[str, Any]]
    columns: List[str]
    total_rows: int


class TransformResponse(BaseModel):
    """โมเดลสำหรับ response การแปลงข้อมูล"""
    data: List[Dict[str, Any]]
    columns: List[str]
    total_rows: int
    matched_count: int
    unmatched_count: int


class HistoryItem(BaseModel):
    """โมเดลสำหรับประวัติการอัพโหลด/แปลงข้อมูล"""
    file_id: str
    original_filename: str
    upload_time: str
    total_rows: int
    status: str


class ApiResponse(BaseModel):
    """โมเดลสำหรับ response ทั่วไปของ API"""
    success: bool
    message: str
    data: Optional[Any] = None
