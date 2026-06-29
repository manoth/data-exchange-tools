"""
Data Exchange Tools - FastAPI Application
แอปพลิเคชันหลักสำหรับแปลงข้อมูล Excel
"""

import os
import uuid
import shutil
import webbrowser
import threading
import sys
import json
import subprocess
import hashlib
import urllib.request
import urllib.parse
import time
import zipfile
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse

from config import (
    APP_DIR, load_config, save_config, test_connection, is_configured,
    public_config, authenticate_admin, change_admin_password
)
from auth import authenticate_user, create_token, verify_token
from models import (
    ConfigModel, LoginRequest, LoginResponse, ChangeAdminPasswordRequest,
    TransformRequest, UploadResponse, TransformResponse,
    HistoryItem, ApiResponse
)
from transform import process_upload, transform_data, export_excel

# กำหนด path
APP_VERSION = "0.0.4"
UPLOADS_DIR = os.path.join(APP_DIR, "uploads")
UPDATE_DIR = os.path.join(APP_DIR, "updates")
UPDATE_MANIFEST = os.path.join(UPDATE_DIR, "manifest.json")
WEB_VERSION_FILE = os.path.join(UPDATE_DIR, "frontend_version.json")
DEFAULT_UPDATE_MANIFEST_URL = "https://github.com/manoth/data-exchange-tools/releases/latest/download/latest.json"
UPDATE_MANIFEST_URL = os.environ.get("UPDATE_MANIFEST_URL", DEFAULT_UPDATE_MANIFEST_URL).strip()
UPDATE_CHECK_INTERVAL_SECONDS = int(os.environ.get("UPDATE_CHECK_INTERVAL_SECONDS", "600"))
BUNDLED_STATIC_DIR = (
    os.path.join(sys._MEIPASS, "static")
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")
    else os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
)
STATIC_OVERRIDE_DIR = os.path.join(APP_DIR, "static") if getattr(sys, "frozen", False) else BUNDLED_STATIC_DIR

# สร้าง FastAPI app
app = FastAPI(title="Data Exchange Tools")

# เก็บข้อมูลอัพโหลดใน memory
upload_store = {}
# เก็บประวัติการใช้งาน
history_store = []
update_cache = {"checked_at": None, "status": None}

# ────────────────────────────────────────────
# Startup Event
# ────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """สร้างโฟลเดอร์ที่จำเป็นเมื่อเริ่มต้นแอป"""
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    os.makedirs(UPDATE_DIR, exist_ok=True)
    if getattr(sys, "frozen", False):
        os.makedirs(STATIC_OVERRIDE_DIR, exist_ok=True)


# ────────────────────────────────────────────
# Static Files & Index
# ────────────────────────────────────────────

def _safe_join(base_dir: str, relative_path: str) -> str:
    base = os.path.abspath(base_dir)
    target = os.path.abspath(os.path.join(base, relative_path))
    if target != base and not target.startswith(base + os.sep):
        return ""
    return target


def _resolve_static_path(relative_path: str) -> str:
    clean_path = relative_path.replace("\\", "/").lstrip("/")
    if getattr(sys, "frozen", False):
        override_path = _safe_join(STATIC_OVERRIDE_DIR, clean_path)
        if override_path and os.path.exists(override_path) and os.path.isfile(override_path):
            return override_path
    bundled_path = _safe_join(BUNDLED_STATIC_DIR, clean_path)
    if bundled_path and os.path.exists(bundled_path) and os.path.isfile(bundled_path):
        return bundled_path
    return ""


@app.get("/static/{path:path}")
async def serve_static(path: str):
    """เสิร์ฟ static files โดยใช้ไฟล์ frontend ที่ update แล้วก่อน แล้วค่อย fallback ไป bundled static"""
    file_path = _resolve_static_path(path)
    if not file_path:
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์")
    return FileResponse(file_path)


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """แสดงหน้าแรก index.html"""
    index_path = _resolve_static_path("index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="""
    <html>
    <head><title>Data Exchange Tools</title></head>
    <body style="display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;background:#1a1a2e;color:#fff;">
        <div style="text-align:center;">
            <h1>⚙️ Data Exchange Tools</h1>
            <p>กรุณาสร้างไฟล์ static/index.html</p>
        </div>
    </body>
    </html>
    """)


# ────────────────────────────────────────────
# Auth Dependency
# ────────────────────────────────────────────

async def get_current_user(request: Request) -> dict:
    """
    ตรวจสอบ JWT token จาก Authorization header
    คืนค่าข้อมูลผู้ใช้หรือ raise 401
    """
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="กรุณาเข้าสู่ระบบก่อนใช้งาน"
        )

    token = auth_header.replace("Bearer ", "")
    user = verify_token(token)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Token ไม่ถูกต้องหรือหมดอายุ กรุณาเข้าสู่ระบบใหม่"
        )

    return user


async def get_current_admin(request: Request) -> dict:
    """ตรวจสอบ token และบังคับว่าต้องเป็น local admin"""
    user = await get_current_user(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="ต้องเข้าสู่ระบบด้วย admin ก่อนตั้งค่าฐานข้อมูล")
    if user.get("must_change_password"):
        raise HTTPException(status_code=403, detail="กรุณาเปลี่ยนรหัสผ่าน admin ก่อน")
    return user


def _version_parts(version: str) -> tuple:
    """แปลง version เป็น tuple สำหรับเทียบแบบง่าย เช่น 1.0.12"""
    parts = []
    for part in str(version or "").split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        parts.append(int(digits or 0))
    return tuple((parts + [0, 0, 0])[:3])


def _get_installed_web_version() -> str:
    if not os.path.exists(WEB_VERSION_FILE):
        return APP_VERSION
    try:
        with open(WEB_VERSION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        version = str(data.get("version") or "")
        return version or APP_VERSION
    except Exception:
        return APP_VERSION


def _get_current_version() -> str:
    web_version = _get_installed_web_version()
    return web_version if _version_parts(web_version) > _version_parts(APP_VERSION) else APP_VERSION


def _load_update_manifest() -> dict:
    if not os.path.exists(UPDATE_MANIFEST):
        return {}
    with open(UPDATE_MANIFEST, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def _load_online_update_manifest(force: bool = False) -> dict:
    if not UPDATE_MANIFEST_URL:
        return {}

    try:
        request = urllib.request.Request(
            UPDATE_MANIFEST_URL,
            headers={
                "User-Agent": f"DataExchangeTools/{APP_VERSION}",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=8) as response:
            if response.status >= 400:
                return {}
            payload = response.read(512 * 1024)
        data = json.loads(payload.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _script_name_for_platform() -> str:
    return "update.bat" if os.name == "nt" else "update.sh"


def _get_manifest_script_url(manifest: dict) -> str:
    if os.name == "nt":
        return str(manifest.get("windows_script_url") or manifest.get("script_url") or "")
    return str(manifest.get("linux_script_url") or manifest.get("script_url") or "")


def _get_manifest_exe_url(manifest: dict) -> str:
    if os.name != "nt":
        return ""
    return str(
        manifest.get("windows_exe_url")
        or manifest.get("exe_url")
        or manifest.get("package_url")
        or ""
    )


def _get_manifest_frontend_zip_url(manifest: dict) -> str:
    return str(
        manifest.get("frontend_zip_url")
        or manifest.get("web_zip_url")
        or manifest.get("static_zip_url")
        or ""
    )


def _get_manifest_sha256(manifest: dict) -> str:
    if os.name == "nt":
        return str(
            manifest.get("windows_sha256")
            or manifest.get("script_sha256")
            or manifest.get("sha256")
            or ""
        ).lower()
    return str(
        manifest.get("linux_sha256")
        or manifest.get("script_sha256")
        or manifest.get("sha256")
        or ""
    ).lower()


def _get_manifest_exe_sha256(manifest: dict) -> str:
    if os.name != "nt":
        return ""
    return str(
        manifest.get("windows_exe_sha256")
        or manifest.get("exe_sha256")
        or manifest.get("package_sha256")
        or ""
    ).lower()


def _get_manifest_frontend_zip_sha256(manifest: dict) -> str:
    return str(
        manifest.get("frontend_zip_sha256")
        or manifest.get("web_zip_sha256")
        or manifest.get("static_zip_sha256")
        or ""
    ).lower()


def _is_safe_update_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _get_update_script_path(manifest: dict) -> str:
    script_name = manifest.get("script")
    if not script_name:
        script_name = _script_name_for_platform()
    script_path = os.path.abspath(os.path.join(UPDATE_DIR, script_name))
    update_root = os.path.abspath(UPDATE_DIR)
    if not script_path.startswith(update_root + os.sep):
        return ""
    return script_path


def _build_update_status(manifest: dict, source: str, online_error: str = "") -> dict:
    current_version = _get_current_version()
    latest_version = str(manifest.get("version") or APP_VERSION)
    script_path = _get_update_script_path(manifest) if manifest else ""
    script_exists = bool(script_path and os.path.exists(script_path))
    script_url = _get_manifest_script_url(manifest) if manifest else ""
    exe_url = _get_manifest_exe_url(manifest) if manifest else ""
    frontend_zip_url = _get_manifest_frontend_zip_url(manifest) if manifest else ""
    online_script_ready = bool(script_url and _is_safe_update_url(script_url) and _get_manifest_sha256(manifest))
    online_exe_ready = bool(exe_url and _is_safe_update_url(exe_url) and _get_manifest_exe_sha256(manifest))
    frontend_ready = bool(
        frontend_zip_url
        and _is_safe_update_url(frontend_zip_url)
        and _get_manifest_frontend_zip_sha256(manifest)
    )
    update_available = (
        bool(manifest)
        and _version_parts(latest_version) > _version_parts(current_version)
        and (script_exists or online_script_ready or online_exe_ready or frontend_ready)
    )
    if update_available:
        message = "พร้อมอัปเดตออนไลน์" if source == "online" else "พร้อมอัปเดต"
    elif online_error:
        message = online_error
    else:
        message = "ยังไม่พบ update script ที่ใหม่กว่า"
    return {
        "success": True,
        "current_version": current_version,
        "app_version": APP_VERSION,
        "frontend_version": _get_installed_web_version(),
        "latest_version": latest_version,
        "update_available": update_available,
        "script_exists": script_exists,
        "online_script": bool(script_url),
        "online_exe": bool(exe_url),
        "frontend_zip": bool(frontend_zip_url),
        "source": source,
        "notes": str(manifest.get("notes") or ""),
        "message": message,
        "manifest": manifest,
    }


def _get_update_status(force: bool = False) -> dict:
    now = datetime.now()
    if (
        not force
        and update_cache.get("checked_at")
        and update_cache.get("status")
        and (now - update_cache["checked_at"]).total_seconds() < UPDATE_CHECK_INTERVAL_SECONDS
    ):
        status = dict(update_cache["status"])
        status.pop("manifest", None)
        return status

    online_manifest = _load_online_update_manifest(force=force)
    if online_manifest:
        status = _build_update_status(online_manifest, "online")
    else:
        local_manifest = _load_update_manifest()
        status = _build_update_status(local_manifest, "local", "เช็ก online ไม่สำเร็จ ใช้ local manifest แทน")

    update_cache["checked_at"] = now
    update_cache["status"] = status
    public_status = dict(status)
    public_status.pop("manifest", None)
    return public_status


def _get_active_update_manifest() -> dict:
    cached = update_cache.get("status") or {}
    manifest = cached.get("manifest")
    if isinstance(manifest, dict) and manifest:
        return manifest
    _get_update_status(force=True)
    cached = update_cache.get("status") or {}
    manifest = cached.get("manifest")
    return manifest if isinstance(manifest, dict) else {}


def _download_url_to_file(url: str, expected_sha256: str, output_path: str, max_bytes: int) -> str:
    if not _is_safe_update_url(url):
        raise ValueError("update URL ต้องเป็น https เท่านั้น")
    if not expected_sha256:
        raise ValueError("online update ต้องระบุ sha256 เพื่อยืนยันไฟล์")

    request = urllib.request.Request(url, headers={"User-Agent": f"DataExchangeTools/{APP_VERSION}"})
    sha256 = hashlib.sha256()
    total = 0
    with urllib.request.urlopen(request, timeout=60) as response, open(output_path, "wb") as f:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise ValueError("ไฟล์ update มีขนาดใหญ่เกินกำหนด")
            sha256.update(chunk)
            f.write(chunk)

    actual_sha256 = sha256.hexdigest().lower()
    if actual_sha256 != expected_sha256:
        try:
            os.remove(output_path)
        except OSError:
            pass
        raise ValueError("sha256 ของไฟล์ update ไม่ตรงกับ manifest")
    return output_path


def _download_update_script(manifest: dict) -> str:
    script_url = _get_manifest_script_url(manifest)
    expected_sha256 = _get_manifest_sha256(manifest)
    if not script_url:
        return _get_update_script_path(manifest)

    os.makedirs(UPDATE_DIR, exist_ok=True)
    script_name = _script_name_for_platform()
    downloaded_path = os.path.abspath(os.path.join(UPDATE_DIR, f"downloaded_{script_name}"))
    _download_url_to_file(script_url, expected_sha256, downloaded_path, 20 * 1024 * 1024)
    if os.name != "nt":
        os.chmod(downloaded_path, 0o700)
    return downloaded_path


def _download_update_exe(manifest: dict) -> str:
    exe_url = _get_manifest_exe_url(manifest)
    expected_sha256 = _get_manifest_exe_sha256(manifest)
    if not exe_url:
        return ""

    os.makedirs(UPDATE_DIR, exist_ok=True)
    exe_path = os.path.abspath(os.path.join(UPDATE_DIR, "DataExchangeTools.new.exe"))
    return _download_url_to_file(exe_url, expected_sha256, exe_path, 500 * 1024 * 1024)


def _download_frontend_zip(manifest: dict) -> str:
    zip_url = _get_manifest_frontend_zip_url(manifest)
    expected_sha256 = _get_manifest_frontend_zip_sha256(manifest)
    if not zip_url:
        return ""

    os.makedirs(UPDATE_DIR, exist_ok=True)
    zip_path = os.path.abspath(os.path.join(UPDATE_DIR, "frontend_update.zip"))
    return _download_url_to_file(zip_url, expected_sha256, zip_path, 80 * 1024 * 1024)


def _validate_zip_member(member_name: str) -> str:
    normalized = member_name.replace("\\", "/").lstrip("/")
    if not normalized or normalized.endswith("/"):
        return ""
    if normalized.startswith("static/"):
        normalized = normalized[len("static/"):]
    if normalized.startswith("../") or "/../" in normalized or normalized == "..":
        return ""
    allowed_roots = ("css/", "js/", "images/", "index.html")
    if not any(normalized == root.rstrip("/") or normalized.startswith(root) for root in allowed_roots):
        return ""
    return normalized


def _apply_frontend_zip(zip_path: str, version: str) -> int:
    if not zip_path or not os.path.exists(zip_path):
        raise ValueError("ไม่พบ frontend zip")

    os.makedirs(STATIC_OVERRIDE_DIR, exist_ok=True)
    extracted_count = 0
    with zipfile.ZipFile(zip_path, "r") as archive:
        for member in archive.infolist():
            relative_name = _validate_zip_member(member.filename)
            if not relative_name:
                continue
            target_path = _safe_join(STATIC_OVERRIDE_DIR, relative_name)
            if not target_path:
                continue
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with archive.open(member, "r") as src, open(target_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
            extracted_count += 1

    if extracted_count == 0:
        raise ValueError("frontend zip ไม่มีไฟล์ที่อนุญาตให้อัปเดต")

    with open(WEB_VERSION_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "version": version,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }, f, ensure_ascii=False, indent=2)
    update_cache["checked_at"] = None
    update_cache["status"] = None
    return extracted_count


def _write_windows_self_updater(new_exe_path: str) -> str:
    if os.name != "nt" or not getattr(sys, "frozen", False):
        raise ValueError("self-update exe ใช้ได้เฉพาะ Windows build แบบ .exe")

    current_exe = os.path.abspath(sys.executable)
    updater_path = os.path.abspath(os.path.join(UPDATE_DIR, "apply_update.bat"))
    log_path = os.path.abspath(os.path.join(UPDATE_DIR, "update.log"))
    bat = f"""@echo off
setlocal
set "NEW_EXE={new_exe_path}"
set "TARGET_EXE={current_exe}"
set "LOG_FILE={log_path}"
echo [%DATE% %TIME%] applying exe update >> "%LOG_FILE%"
timeout /t 3 /nobreak >nul
copy /Y "%NEW_EXE%" "%TARGET_EXE%" >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
  echo [%DATE% %TIME%] first copy failed, retrying >> "%LOG_FILE%"
  timeout /t 4 /nobreak >nul
  copy /Y "%NEW_EXE%" "%TARGET_EXE%" >> "%LOG_FILE%" 2>&1
)
if errorlevel 1 (
  echo [%DATE% %TIME%] update failed >> "%LOG_FILE%"
  exit /b 1
)
echo [%DATE% %TIME%] update complete, restarting >> "%LOG_FILE%"
start "" "%TARGET_EXE%"
exit /b 0
"""
    with open(updater_path, "w", encoding="utf-8") as f:
        f.write(bat)
    return updater_path


def _schedule_process_exit(delay_seconds: float = 1.0):
    def stop_process():
        time.sleep(delay_seconds)
        os._exit(0)

    timer = threading.Thread(target=stop_process, daemon=True)
    timer.start()


# ────────────────────────────────────────────
# Config Endpoints (ไม่ต้อง auth)
# ────────────────────────────────────────────

@app.get("/api/config/status")
async def config_status():
    """ตรวจสอบสถานะการตั้งค่า"""
    return {"configured": is_configured()}


@app.get("/api/config")
async def config_get(current_admin: dict = Depends(get_current_admin)):
    """ดึงการตั้งค่าฐานข้อมูลแบบไม่เปิดเผยรหัสผ่าน"""
    return {"success": True, "config": public_config()}


@app.post("/api/config/test")
async def config_test(config: ConfigModel, current_admin: dict = Depends(get_current_admin)):
    """ทดสอบการเชื่อมต่อฐานข้อมูล"""
    result = test_connection(config.model_dump())
    return result


@app.post("/api/config/save")
async def config_save(config: ConfigModel, current_admin: dict = Depends(get_current_admin)):
    """บันทึกการตั้งค่าฐานข้อมูล"""
    # ทดสอบการเชื่อมต่อก่อนบันทึก
    test_result = test_connection(config.model_dump())
    if not test_result.get("success"):
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": f"ไม่สามารถเชื่อมต่อฐานข้อมูลได้: {test_result.get('message', '')}"
            }
        )

    result = save_config(config.model_dump())
    return result


@app.post("/api/config")
async def config_save_alias(config: ConfigModel, current_admin: dict = Depends(get_current_admin)):
    """Alias สำหรับ frontend รุ่นใหม่"""
    return await config_save(config, current_admin)


# ────────────────────────────────────────────
# Auth Endpoints
# ────────────────────────────────────────────

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """เข้าสู่ระบบ"""
    try:
        if request.username == "admin":
            user = authenticate_admin(request.username, request.password)
        else:
            user = authenticate_user(request.username, request.password)

        if not user:
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "token": "",
                    "user": {},
                    "message": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"
                }
            )

        token = create_token(user)

        return {
            "success": True,
            "token": token,
                "user": {
                    "name": user.get("name", ""),
                    "position": user.get("position", ""),
                    "role": user.get("role", "user"),
                    "must_change_password": bool(user.get("must_change_password", False))
                },
                "username": user.get("loginname", ""),
                "name": user.get("name", ""),
                "position": user.get("position", ""),
                "role": user.get("role", "user"),
                "must_change_password": bool(user.get("must_change_password", False)),
                "configured": is_configured()
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "token": "",
                "user": {},
                "message": f"เกิดข้อผิดพลาดในการเข้าสู่ระบบ: {e}"
            }
        )


@app.post("/api/login")
async def login_alias(request: LoginRequest):
    """Alias สำหรับ frontend รุ่นใหม่"""
    return await login(request)


@app.post("/api/admin/change-password")
async def admin_change_password(
    request: ChangeAdminPasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """เปลี่ยนรหัสผ่าน local admin"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="ต้องเข้าสู่ระบบด้วย admin")
    result = change_admin_password(request.old_password, request.new_password)
    if not result.get("success"):
        return JSONResponse(status_code=400, content=result)
    admin_user = authenticate_admin("admin", request.new_password)
    result["token"] = create_token(admin_user)
    result["user"] = {
        "name": admin_user.get("name", ""),
        "position": admin_user.get("position", ""),
        "role": "admin",
        "must_change_password": False,
    }
    return result


@app.post("/api/admin/shutdown")
async def admin_shutdown(current_admin: dict = Depends(get_current_admin)):
    """ปิด service ตามคำสั่งของ admin"""
    def stop_server():
        os._exit(0)

    timer = threading.Timer(0.8, stop_server)
    timer.daemon = True
    timer.start()
    return {"success": True, "message": "กำลังปิด service"}


@app.get("/api/version/status")
async def version_status(force: bool = False, current_admin: dict = Depends(get_current_admin)):
    """ตรวจสอบว่ามี update script รุ่นใหม่หรือไม่"""
    try:
        return _get_update_status(force=force)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"ไม่สามารถตรวจสอบ update ได้: {e}",
                "current_version": APP_VERSION,
                "latest_version": APP_VERSION,
                "update_available": False,
                "script_exists": False,
            }
        )


@app.post("/api/admin/update")
async def admin_update(current_admin: dict = Depends(get_current_admin)):
    """ดาวน์โหลดและใช้ update จาก online manifest หรือ local script"""
    try:
        status = _get_update_status(force=True)
        if not status.get("update_available"):
            return JSONResponse(status_code=400, content=status)

        manifest = _get_active_update_manifest()
        exe_url = _get_manifest_exe_url(manifest)
        frontend_zip_url = _get_manifest_frontend_zip_url(manifest)
        if frontend_zip_url and not exe_url:
            zip_path = _download_frontend_zip(manifest)
            file_count = _apply_frontend_zip(zip_path, status["latest_version"])
            return {
                "success": True,
                "message": f"อัปเดตหน้าเว็บสำเร็จ {file_count} ไฟล์ กรุณา refresh หน้าเว็บ",
                "current_version": _get_current_version(),
                "latest_version": status["latest_version"],
                "reload_required": True,
            }

        if exe_url:
            new_exe_path = _download_update_exe(manifest)
            updater_path = _write_windows_self_updater(new_exe_path)
            log_path = os.path.join(UPDATE_DIR, "update.log")
            log_file = open(log_path, "a", encoding="utf-8")
            log_file.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] start self-update {status['latest_version']}\n")
            log_file.flush()
            subprocess.Popen(
                ["cmd", "/c", updater_path],
                cwd=UPDATE_DIR,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            )
            _schedule_process_exit(1.0)
            return {
                "success": True,
                "message": "ดาวน์โหลด update แล้ว ระบบจะปิด service และเปิดโปรแกรมเวอร์ชันใหม่ให้อัตโนมัติ",
                "current_version": APP_VERSION,
                "latest_version": status["latest_version"],
            }

        script_path = _download_update_script(manifest)
        if not script_path or not os.path.exists(script_path):
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "ไม่พบ update script ที่พร้อมใช้งาน"}
            )
        log_path = os.path.join(UPDATE_DIR, "update.log")
        command = ["cmd", "/c", script_path] if os.name == "nt" else ["sh", script_path]
        log_file = open(log_path, "a", encoding="utf-8")
        log_file.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] start update {status['latest_version']}\n")
        log_file.flush()
        subprocess.Popen(
            command,
            cwd=UPDATE_DIR,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            close_fds=(os.name != "nt"),
        )
        return {
            "success": True,
            "message": "เริ่มรัน update script แล้ว กรุณารอสักครู่และเปิดโปรแกรมใหม่หากสคริปต์ต้อง restart",
            "current_version": APP_VERSION,
            "latest_version": status["latest_version"],
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"ไม่สามารถเริ่ม update ได้: {e}"}
        )


@app.post("/api/auth/logout")
async def logout():
    """ออกจากระบบ"""
    return {"success": True, "message": "ออกจากระบบสำเร็จ"}


# ────────────────────────────────────────────
# Protected Endpoints (ต้อง auth)
# ────────────────────────────────────────────

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """อัพโหลดไฟล์ Excel"""
    try:
        # ตรวจสอบนามสกุลไฟล์
        if not file.filename.lower().endswith('.xlsx'):
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "กรุณาอัพโหลดไฟล์ Excel (.xlsx) เท่านั้น"
                }
            )

        # สร้าง file_id
        file_id = str(uuid.uuid4())

        # บันทึกไฟล์
        os.makedirs(UPLOADS_DIR, exist_ok=True)
        file_ext = os.path.splitext(file.filename)[1]
        saved_filename = f"{file_id}{file_ext}"
        file_path = os.path.join(UPLOADS_DIR, saved_filename)

        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # ประมวลผลไฟล์
        result = process_upload(file_path)

        # เก็บข้อมูลใน memory
        upload_store[file_id] = {
            "file_path": file_path,
            "original_filename": file.filename,
            "columns": result["columns"],
            "data": result["data"],
            "facilities": result.get("facilities", []),
            "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_rows": len(result["data"]),
            "status": "uploaded"
        }

        # เพิ่มประวัติ
        history_store.append({
            "file_id": file_id,
            "original_filename": file.filename,
            "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_rows": len(result["data"]),
            "status": "uploaded"
        })

        return {
            "success": True,
            "file_id": file_id,
            "preview": result["preview"],
            "columns": result["columns"],
            "total_rows": len(result["data"]),
            "facilities": result.get("facilities", [])
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"เกิดข้อผิดพลาดในการอัพโหลด: {e}"
            }
        )


@app.post("/api/transform")
async def transform(
    request: TransformRequest,
    current_user: dict = Depends(get_current_user)
):
    """แปลงข้อมูล"""
    try:
        file_id = request.file_id

        if file_id not in upload_store:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "ไม่พบไฟล์ที่ระบุ กรุณาอัพโหลดใหม่"
                }
            )

        upload_info = upload_store[file_id]
        data = upload_info["data"]
        columns = upload_info["columns"]

        # แปลงข้อมูล
        result = transform_data(file_id, data, columns, request.hoscodes)

        # ส่งออกเป็น Excel
        output_path = export_excel(
            result["data"],
            result["columns"],
            upload_info["original_filename"]
        )

        # อัพเดทข้อมูลใน store
        upload_store[file_id]["transformed_data"] = result["data"]
        upload_store[file_id]["output_path"] = output_path
        upload_store[file_id]["status"] = "completed"
        upload_store[file_id]["matched_count"] = result["matched_count"]
        upload_store[file_id]["unmatched_count"] = result["unmatched_count"]
        upload_store[file_id]["selected_hoscodes"] = request.hoscodes

        # อัพเดทประวัติ
        for item in history_store:
            if item["file_id"] == file_id:
                item["status"] = "completed"
                break

        return {
            "success": True,
            "data": result["data"],
            "columns": result["columns"],
            "total_rows": len(result["data"]),
            "matched_count": result["matched_count"],
            "unmatched_count": result["unmatched_count"],
            "file_id": file_id
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"เกิดข้อผิดพลาดในการแปลงข้อมูล: {e}"
            }
        )


@app.get("/api/download/{file_id}")
async def download_file(
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """ดาวน์โหลดไฟล์ Excel ที่แปลงแล้ว"""
    try:
        if file_id not in upload_store:
            raise HTTPException(
                status_code=404,
                detail="ไม่พบไฟล์ที่ระบุ"
            )

        upload_info = upload_store[file_id]
        output_path = upload_info.get("output_path")

        if not output_path or not os.path.exists(output_path):
            raise HTTPException(
                status_code=404,
                detail="ไม่พบไฟล์ที่แปลงแล้ว กรุณาทำการแปลงข้อมูลก่อน"
            )

        # สร้างชื่อไฟล์สำหรับดาวน์โหลด
        download_filename = os.path.basename(output_path)

        return FileResponse(
            path=output_path,
            filename=download_filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"เกิดข้อผิดพลาดในการดาวน์โหลด: {e}"
        )


@app.post("/api/export")
async def export_file(
    request: TransformRequest,
    current_user: dict = Depends(get_current_user)
):
    """Alias สำหรับดาวน์โหลดไฟล์ Excel ที่แปลงแล้ว"""
    return await download_file(request.file_id, current_user)


@app.get("/api/history")
async def get_history(current_user: dict = Depends(get_current_user)):
    """ดึงประวัติการอัพโหลด/แปลงข้อมูล"""
    return {
        "success": True,
        "data": list(reversed(history_store))
    }


# ────────────────────────────────────────────
# Entry Point
# ────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    # PyInstaller --windowed on Windows sets stdout/stderr to None. Uvicorn's
    # logging formatter expects them to exist, so point them at the null device.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")

    # พิมพ์ banner
    print()
    print("=" * 50)
    print("  ⚙️  Data Exchange Tools")
    print("=" * 50)
    print(f"  🌐 URL: http://localhost:8899")
    print(f"  📁 Uploads: {UPLOADS_DIR}")
    print("=" * 50)
    print()

    # เปิด browser หลังจาก 1.5 วินาที
    def open_browser():
        webbrowser.open("http://localhost:8899")

    timer = threading.Timer(1.5, open_browser)
    timer.daemon = True
    timer.start()

    # เริ่ม server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8899,
        log_level="info"
    )
