"""
Data Exchange Tools - FastAPI Application
แอปพลิเคชันหลักสำหรับแปลงข้อมูล Excel
"""

import os
import uuid
import shutil
import webbrowser
import threading
import asyncio
import sys
import json
import subprocess
import hashlib
import urllib.parse
import urllib.request
import urllib.error
import time
import zipfile
import socket
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse

from config import (
    APP_DIR, load_config, save_config, test_connection, is_configured,
    public_config, authenticate_admin, change_admin_password,
    load_agent_config, save_agent_api_key, clear_agent_api_key, public_agent_config
)
from auth import authenticate_user, create_token, verify_token
from models import (
    ConfigModel, LoginRequest, LoginResponse, ChangeAdminPasswordRequest,
    TransformRequest, UploadResponse, TransformResponse,
    HistoryItem, ApiResponse
)
from transform import process_upload, transform_data, export_excel
from database import get_connection

# กำหนด path
APP_VERSION = "0.1.1"
APP_HOST = os.environ.get("APP_HOST", "0.0.0.0")
APP_PORT = int(os.environ.get("PORT", "8899"))
APP_URL = os.environ.get("APP_URL", f"http://localhost:{APP_PORT}")
SERVICE_MODE = "--service" in sys.argv or os.environ.get("DATA_EXCHANGE_SERVICE_MODE", "").strip().lower() in ("1", "true", "yes")
CENTRAL_API_URL = os.environ.get("CENTRAL_API_URL", "https://apicpho.moph.go.th").rstrip("/")
CENTRAL_API_ENROLLMENT_TOKEN = os.environ.get("CENTRAL_API_ENROLLMENT_TOKEN", "data-exchange-agent-enroll-dev-token")
AGENT_HEARTBEAT_INTERVAL_SECONDS = int(os.environ.get("AGENT_HEARTBEAT_INTERVAL_SECONDS", "30"))
UPLOADS_DIR = os.path.join(APP_DIR, "uploads")
UPDATE_DIR = os.path.join(APP_DIR, "updates")
UPDATE_MANIFEST = os.path.join(UPDATE_DIR, "manifest.json")
WEB_VERSION_FILE = os.path.join(UPDATE_DIR, "frontend_version.json")
DEFAULT_UPDATE_MANIFEST_URL = "https://github.com/manoth/data-exchange-tools/releases/latest/download/latest.json"
UPDATE_MANIFEST_URL = os.environ.get("UPDATE_MANIFEST_URL", DEFAULT_UPDATE_MANIFEST_URL).strip()
UPDATE_CHECK_INTERVAL_SECONDS = int(os.environ.get("UPDATE_CHECK_INTERVAL_SECONDS", "600"))
AUTO_UPDATE_ON_STARTUP = os.environ.get("AUTO_UPDATE_ON_STARTUP", "1").strip().lower() not in ("0", "false", "no", "off")
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
recent_upload_cache = {}
upload_cache_lock = threading.Lock()
update_cache = {"checked_at": None, "status": None, "last_error": ""}
startup_update_state = {
    "running": False,
    "checked_at": None,
    "success": None,
    "message": "",
    "from_version": "",
    "to_version": "",
}
startup_update_lock = threading.Lock()
agent_heartbeat_state = {
    "running": False,
    "last_success": None,
    "last_error": "",
    "facility_code": "",
    "facility_name": "",
}
agent_heartbeat_lock = threading.Lock()

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
    _ensure_windows_client_integration()
    _start_startup_auto_update()
    _start_agent_heartbeat()


def _get_agent_uid() -> str:
    return f"data-exchange-tools-{socket.gethostname()}-{APP_PORT}"


def _read_hospital_info_from_his() -> dict:
    """Read local facility identity from HosXP opdconfig."""
    if not is_configured():
        return {
            "db_status": "unknown",
            "facility_code": "",
            "facility_name": "",
            "error": "ยังไม่ได้ตั้งค่าฐานข้อมูล HIS",
        }

    connection = None
    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT hospitalcode, hospitalname
                FROM opdconfig
                WHERE hospitalcode IS NOT NULL OR hospitalname IS NOT NULL
                LIMIT 1
                """
            )
            row = cursor.fetchone() or {}
        return {
            "db_status": "ok",
            "facility_code": str(row.get("hospitalcode") or "").strip(),
            "facility_name": str(row.get("hospitalname") or "").strip(),
            "error": "",
        }
    except Exception as exc:
        return {
            "db_status": "failed",
            "facility_code": "",
            "facility_name": "",
            "error": str(exc),
        }
    finally:
        if connection:
            try:
                connection.close()
            except Exception:
                pass


def _send_agent_heartbeat() -> dict:
    _ensure_agent_api_key()
    hospital = _read_hospital_info_from_his()
    payload = {
        "agentUid": _get_agent_uid(),
        "facilityCode": hospital["facility_code"],
        "facilityName": hospital["facility_name"],
        "machineName": socket.gethostname(),
        "appVersion": APP_VERSION,
        "frontendVersion": _get_installed_web_version(),
        "dbStatus": hospital["db_status"],
        "status": "online",
        "payload": {
            "agentUrl": APP_URL,
            "appPort": APP_PORT,
            "serviceMode": SERVICE_MODE,
            "hospitalcode": hospital["facility_code"],
            "hospitalname": hospital["facility_name"],
            "hisError": hospital["error"],
        },
    }
    def send_once():
        request = urllib.request.Request(
            f"{CENTRAL_API_URL}/api/agents/heartbeat",
            data=json.dumps(payload).encode("utf-8"),
            headers=_agent_api_headers(),
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=8) as response:
            return json.loads(response.read().decode("utf-8"))

    try:
        return send_once()
    except urllib.error.HTTPError as exc:
        if exc.code not in (401, 403):
            raise
        _ensure_agent_api_key(force=True)
        return send_once()


def _central_api_json(path: str, method: str = "GET", payload: dict = None) -> dict:
    _ensure_agent_api_key()
    data = None
    headers = _agent_api_headers()
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{CENTRAL_API_URL}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _check_central_api_health() -> dict:
    request = urllib.request.Request(
        f"{CENTRAL_API_URL}/api/health",
        headers={"Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            result = json.loads(response.read().decode("utf-8"))
        if result.get("ok"):
            return {"online": True, "message": "API Center พร้อมใช้งาน"}
        return {"online": False, "message": result.get("message") or "API Center ตอบกลับไม่สมบูรณ์"}
    except Exception as exc:
        return {"online": False, "message": f"ไม่สามารถเชื่อมต่อ API Center ได้: {exc}"}


def _agent_api_headers() -> dict:
    agent_config = load_agent_config()
    headers = {
        "Content-Type": "application/json",
        "X-Agent-Uid": _get_agent_uid(),
    }
    if agent_config.get("api_key"):
        headers["X-Agent-Key"] = agent_config["api_key"]
    return headers


def _ensure_agent_api_key(force: bool = False) -> dict:
    agent_config = load_agent_config()
    saved_api_url = (agent_config.get("api_center_url") or "").rstrip("/")
    if (
        not force
        and agent_config.get("api_key")
        and (not saved_api_url or saved_api_url == CENTRAL_API_URL)
    ):
        return {
            "configured": True,
            "api_key_prefix": agent_config.get("api_key_prefix", ""),
        }
    if force or (agent_config.get("api_key") and saved_api_url and saved_api_url != CENTRAL_API_URL):
        clear_agent_api_key()

    hospital = _read_hospital_info_from_his()
    payload = {
        "agentUid": _get_agent_uid(),
        "facilityCode": hospital["facility_code"],
        "facilityName": hospital["facility_name"],
        "machineName": socket.gethostname(),
        "appVersion": APP_VERSION,
        "frontendVersion": _get_installed_web_version(),
        "dbStatus": hospital["db_status"],
    }
    request = urllib.request.Request(
        f"{CENTRAL_API_URL}/api/agents/register",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Agent-Enrollment-Token": CENTRAL_API_ENROLLMENT_TOKEN,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        result = json.loads(response.read().decode("utf-8"))

    data = result.get("data") or {}
    api_key = data.get("apiKey")
    api_key_prefix = data.get("apiKeyPrefix") or ""
    if not api_key:
        raise RuntimeError("API Center ไม่ได้ส่ง Agent API key กลับมา กรุณา rotate key จาก Control แล้วตั้งค่าใหม่")

    save_result = save_agent_api_key(api_key, api_key_prefix, CENTRAL_API_URL)
    if not save_result.get("success"):
        raise RuntimeError(save_result.get("message") or "บันทึก Agent API key ไม่สำเร็จ")

    return {
        "configured": True,
        "api_key_prefix": api_key_prefix,
    }


def _get_agent_heartbeat_status() -> dict:
    with agent_heartbeat_lock:
        state = dict(agent_heartbeat_state)
    agent_config = public_agent_config()
    saved_api_url = (agent_config.get("api_center_url") or "").rstrip("/")
    return {
        **state,
        "api_key_configured": agent_config["api_key_configured"],
        "api_key_prefix": agent_config["api_key_prefix"],
        "api_key_registered_at": agent_config["registered_at"],
        "api_key_api_center_url": saved_api_url,
        "api_key_url_matches": not saved_api_url or saved_api_url == CENTRAL_API_URL,
    }


def _execute_agent_command(command: dict) -> tuple:
    command_type = command.get("commandType") or command.get("command_type") or ""
    payload = command.get("payload") or {}
    hospital = _read_hospital_info_from_his()

    if command_type == "health_check":
        return True, {
            "message": "agent พร้อมใช้งาน",
            "agentUid": _get_agent_uid(),
            "machineName": socket.gethostname(),
            "appUrl": APP_URL,
            "serviceMode": SERVICE_MODE,
            "dbStatus": hospital["db_status"],
        }

    if command_type == "db_check":
        return hospital["db_status"] == "ok", {
            "message": "เชื่อมต่อฐานข้อมูล HIS สำเร็จ" if hospital["db_status"] == "ok" else "เชื่อมต่อฐานข้อมูล HIS ไม่สำเร็จ",
            "dbStatus": hospital["db_status"],
            "error": hospital["error"],
        }

    if command_type == "version_check":
        return True, {
            "message": "ตรวจสอบเวอร์ชันสำเร็จ",
            "appVersion": APP_VERSION,
            "frontendVersion": _get_installed_web_version(),
        }

    if command_type == "refresh_opdconfig":
        return hospital["db_status"] == "ok", {
            "message": "อ่านข้อมูลหน่วยบริการจาก opdconfig สำเร็จ" if hospital["db_status"] == "ok" else "อ่านข้อมูลหน่วยบริการไม่สำเร็จ",
            "hospitalcode": hospital["facility_code"],
            "hospitalname": hospital["facility_name"],
            "error": hospital["error"],
        }

    if command_type == "check_update":
        update_info = _get_update_status(force=True)
        return True, {
            "message": "ตรวจสอบ update สำเร็จ",
            "update": update_info,
        }

    if command_type == "send_latest_log":
        lines = int(payload.get("lines", 100) or 100) if isinstance(payload, dict) else 100
        log_path = os.path.join(UPDATE_DIR, "update.log")
        content = ""
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8", errors="ignore") as log_file:
                content = "".join(log_file.readlines()[-lines:])
        return True, {
            "message": "ส่ง log ล่าสุดสำเร็จ",
            "logPath": log_path,
            "content": content,
        }

    if command_type == "restart_service":
        return True, {
            "message": "รับคำสั่ง restart แล้ว แต่โหมด dev ยังไม่ restart อัตโนมัติ",
            "payload": payload,
        }

    return False, {
        "message": f"ไม่รู้จักคำสั่ง: {command_type}",
        "payload": payload,
    }


def _pull_and_execute_agent_commands():
    encoded_uid = urllib.parse.quote(_get_agent_uid(), safe="")
    response = _central_api_json(f"/api/agents/uid/{encoded_uid}/commands/pull")
    commands = response.get("data") or []
    for command in commands:
        command_id = command.get("id")
        try:
            success, result = _execute_agent_command(command)
            _central_api_json(
                f"/api/agents/commands/{command_id}/result",
                method="POST",
                payload={
                    "status": "success" if success else "failed",
                    "result": result,
                },
            )
        except Exception as exc:
            if command_id:
                _central_api_json(
                    f"/api/agents/commands/{command_id}/result",
                    method="POST",
                    payload={
                        "status": "failed",
                        "result": {"message": str(exc)},
                    },
                )


def _agent_heartbeat_worker():
    while True:
        try:
            _send_agent_heartbeat()
            _pull_and_execute_agent_commands()
            hospital = _read_hospital_info_from_his()
            with agent_heartbeat_lock:
                agent_heartbeat_state.update({
                    "last_success": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "last_error": "",
                    "facility_code": hospital["facility_code"],
                    "facility_name": hospital["facility_name"],
                })
        except Exception as exc:
            with agent_heartbeat_lock:
                agent_heartbeat_state["last_error"] = str(exc)
        time.sleep(max(10, AGENT_HEARTBEAT_INTERVAL_SECONDS))


def _start_agent_heartbeat():
    if not CENTRAL_API_URL:
        return
    with agent_heartbeat_lock:
        if agent_heartbeat_state["running"]:
            return
        agent_heartbeat_state["running"] = True
    threading.Thread(target=_agent_heartbeat_worker, daemon=True).start()


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
    return FileResponse(file_path, headers={"Cache-Control": "no-store"})


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


@app.get("/manual/open", response_class=HTMLResponse)
async def open_manual_html():
    """เปิดคู่มือการใช้งานแบบหน้าเว็บในระบบ"""
    manual_path = _resolve_static_path("manual.html")
    if not manual_path:
        manual_path = os.path.join(APP_DIR, "คู่มือ", "manual.html")
    if not os.path.exists(manual_path):
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์คู่มือการใช้งาน")
    with open(manual_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/manual/assets/{filename}")
async def serve_manual_asset(filename: str):
    """เสิร์ฟภาพประกอบคู่มือจาก static ที่ update ได้ หรือ fallback ไปโฟลเดอร์คู่มือ"""
    safe_name = os.path.basename(filename)
    static_asset_path = _resolve_static_path(f"images/manual/{safe_name}")
    if static_asset_path:
        return FileResponse(static_asset_path, headers={"Cache-Control": "no-store"})

    manual_image_dir = os.path.join(APP_DIR, "คู่มือ", "images", "manual-web")
    asset_path = _safe_join(manual_image_dir, safe_name)
    if not asset_path or not os.path.exists(asset_path) or not os.path.isfile(asset_path):
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์ภาพคู่มือ")
    return FileResponse(asset_path, headers={"Cache-Control": "no-store"})


@app.get("/manual/pdf")
async def open_manual_pdf():
    """เปิดคู่มือการใช้งาน PDF รุ่นเอกสาร หากมีไฟล์อยู่"""
    manual_path = os.path.join(APP_DIR, "คู่มือ", "DataExchangeTools_User_Manual.pdf")
    if not os.path.exists(manual_path):
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์คู่มือการใช้งาน PDF")
    return FileResponse(
        manual_path,
        media_type="application/pdf",
        filename="DataExchangeTools_User_Manual.pdf"
    )


@app.get("/manual/docx")
async def download_manual_docx():
    """ดาวน์โหลดคู่มือการใช้งาน Word"""
    manual_path = os.path.join(APP_DIR, "คู่มือ", "DataExchangeTools_User_Manual.docx")
    if not os.path.exists(manual_path):
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์คู่มือการใช้งาน")
    return FileResponse(
        manual_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="DataExchangeTools_User_Manual.docx"
    )


@app.get("/login", response_class=HTMLResponse)
@app.get("/change-admin-password", response_class=HTMLResponse)
@app.get("/config", response_class=HTMLResponse)
@app.get("/service", response_class=HTMLResponse)
@app.get("/upload", response_class=HTMLResponse)
@app.get("/history", response_class=HTMLResponse)
@app.get("/settings", response_class=HTMLResponse)
@app.get("/manual", response_class=HTMLResponse)
async def serve_app_route():
    """รองรับ frontend routes เพื่อให้ refresh แล้วอยู่หน้าเดิม"""
    return await serve_index()


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
        update_cache["last_error"] = "ไม่ได้กำหนด UPDATE_MANIFEST_URL"
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
                update_cache["last_error"] = f"HTTP {response.status} จาก online manifest"
                return {}
            payload = response.read(512 * 1024)
        data = json.loads(payload.decode("utf-8"))
        if not isinstance(data, dict):
            update_cache["last_error"] = "รูปแบบ latest.json ไม่ใช่ JSON object"
            return {}
        update_cache["last_error"] = ""
        return data
    except urllib.error.HTTPError as e:
        update_cache["last_error"] = f"HTTP {e.code}: {e.reason}"
        return {}
    except urllib.error.URLError as e:
        update_cache["last_error"] = f"เชื่อมต่อ URL ไม่ได้: {e.reason}"
        return {}
    except json.JSONDecodeError as e:
        update_cache["last_error"] = f"อ่าน latest.json ไม่ได้: {e}"
        return {}
    except Exception as e:
        update_cache["last_error"] = str(e)[:300]
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
        reason = update_cache.get("last_error") or "ไม่ทราบสาเหตุ"
        status = _build_update_status(
            local_manifest,
            "local",
            f"เช็ก online ไม่สำเร็จ ({reason}) ใช้ local manifest แทน",
        )

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
    allowed_roots = ("css/", "js/", "images/", "index.html", "manual.html", "manual_fragment.html")
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


def _is_port_open(host: str = "127.0.0.1", port: int = APP_PORT) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def _write_update_log(message: str):
    try:
        os.makedirs(UPDATE_DIR, exist_ok=True)
        log_path = os.path.join(UPDATE_DIR, "update.log")
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}\n")
    except Exception:
        pass


def _set_startup_update_state(**kwargs):
    with startup_update_lock:
        startup_update_state.update(kwargs)


def _get_startup_update_state() -> dict:
    with startup_update_lock:
        return dict(startup_update_state)


def _run_startup_auto_update():
    if not AUTO_UPDATE_ON_STARTUP:
        _set_startup_update_state(
            running=False,
            checked_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            success=True,
            message="ปิดใช้งาน auto update ตอนเริ่ม service",
        )
        return

    _set_startup_update_state(
        running=True,
        checked_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        success=None,
        message="กำลังตรวจสอบ update ตอนเริ่ม service",
    )
    _write_update_log("startup auto-update: checking online manifest")

    try:
        status = _get_update_status(force=True)
        if not status.get("update_available"):
            message = status.get("message") or "ไม่มี update ใหม่"
            _set_startup_update_state(
                running=False,
                success=True,
                message=f"startup auto-update: {message}",
                from_version=status.get("current_version", ""),
                to_version=status.get("latest_version", ""),
            )
            _write_update_log(f"startup auto-update: no update ({message})")
            return

        manifest = _get_active_update_manifest()
        latest_version = status.get("latest_version") or str(manifest.get("version") or "")
        current_version = status.get("current_version") or _get_current_version()
        frontend_zip_url = _get_manifest_frontend_zip_url(manifest)
        exe_url = _get_manifest_exe_url(manifest)

        if exe_url and os.name == "nt" and getattr(sys, "frozen", False):
            new_exe_path = _download_update_exe(manifest)
            updater_path = _write_windows_self_updater(new_exe_path)
            log_path = os.path.join(UPDATE_DIR, "update.log")
            log_file = open(log_path, "a", encoding="utf-8")
            log_file.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] startup self-update {latest_version}\n")
            log_file.flush()
            subprocess.Popen(
                ["cmd", "/c", updater_path],
                cwd=UPDATE_DIR,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            )
            message = f"ดาวน์โหลด exe v{latest_version} แล้ว กำลัง restart service เพื่อใช้เวอร์ชันใหม่"
            _set_startup_update_state(
                running=False,
                success=True,
                message=message,
                from_version=current_version,
                to_version=latest_version,
            )
            _write_update_log(f"startup auto-update: {message}")
            _schedule_process_exit(1.0)
            return

        if frontend_zip_url:
            zip_path = _download_frontend_zip(manifest)
            file_count = _apply_frontend_zip(zip_path, latest_version)
            message = f"อัปเดต frontend เป็น v{latest_version} สำเร็จ {file_count} ไฟล์"
            _set_startup_update_state(
                running=False,
                success=True,
                message=message,
                from_version=current_version,
                to_version=latest_version,
            )
            _write_update_log(f"startup auto-update: {message}")
            return

        if exe_url:
            message = "พบ update แบบ exe/backend แต่ auto self-update ใช้ได้เฉพาะ Windows build แบบ .exe"
        else:
            message = "พบ update แต่ไม่มี frontend zip ที่ apply อัตโนมัติได้"
        _set_startup_update_state(
            running=False,
            success=False,
            message=message,
            from_version=current_version,
            to_version=latest_version,
        )
        _write_update_log(f"startup auto-update: skipped ({message})")
    except Exception as e:
        message = f"startup auto-update ไม่สำเร็จ: {e}"
        _set_startup_update_state(
            running=False,
            success=False,
            message=message,
        )
        _write_update_log(message)


def _start_startup_auto_update():
    if not AUTO_UPDATE_ON_STARTUP:
        _run_startup_auto_update()
        return
    worker = threading.Thread(target=_run_startup_auto_update, daemon=True)
    worker.start()


def _desktop_dir() -> str:
    user_profile = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    candidates = [
        os.path.join(user_profile, "Desktop"),
        os.path.join(user_profile, "OneDrive", "Desktop"),
    ]
    for path in candidates:
        if os.path.isdir(path):
            return path
    return candidates[0]


def _ensure_desktop_shortcut():
    if os.name != "nt" or not getattr(sys, "frozen", False):
        return

    desktop = _desktop_dir()
    os.makedirs(desktop, exist_ok=True)
    shortcut_path = os.path.join(desktop, "Data Exchange Tools.url")
    content = "\n".join([
        "[InternetShortcut]",
        f"URL={APP_URL}",
        f"IconFile={os.path.abspath(sys.executable)}",
        "IconIndex=0",
        "",
    ])
    try:
        existing = ""
        if os.path.exists(shortcut_path):
            with open(shortcut_path, "r", encoding="utf-8", errors="ignore") as f:
                existing = f.read()
        if existing != content:
            with open(shortcut_path, "w", encoding="utf-8") as f:
                f.write(content)
        _write_update_log(f"windows startup: desktop shortcut ready {shortcut_path}")
    except Exception as e:
        _write_update_log(f"windows startup: desktop shortcut failed: {e}")


def _ensure_windows_startup_task():
    if os.name != "nt" or not getattr(sys, "frozen", False):
        return

    task_name = "DataExchangeToolsService"
    exe_path = os.path.abspath(sys.executable)
    task_run = f'"{exe_path}" --service'
    command = [
        "schtasks",
        "/Create",
        "/TN", task_name,
        "/SC", "ONLOGON",
        "/TR", task_run,
        "/RL", "LIMITED",
        "/F",
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode == 0:
            _write_update_log(f"windows startup: scheduled task ready ({task_name})")
        else:
            detail = (result.stderr or result.stdout or "").strip()
            _write_update_log(f"windows startup: scheduled task failed: {detail}")
    except Exception as e:
        _write_update_log(f"windows startup: scheduled task failed: {e}")


def _ensure_windows_client_integration():
    _ensure_desktop_shortcut()
    _ensure_windows_startup_task()


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


@app.get("/api/agent/api-center")
async def agent_api_center_info(current_admin: dict = Depends(get_current_admin)):
    """แสดงข้อมูลเส้นทาง API Center ที่ Agent ใช้งานแบบอ่านอย่างเดียว"""
    agent_config = public_agent_config()
    api_health = _check_central_api_health()
    heartbeat_status = _get_agent_heartbeat_status()
    return {
        "success": True,
        "api_center_url": CENTRAL_API_URL,
        "heartbeat_endpoint": f"{CENTRAL_API_URL}/api/agents/heartbeat",
        "death_lookup_endpoint": f"{CENTRAL_API_URL}/api/agents/death-persons/lookup",
        "agent_uid": _get_agent_uid(),
        "api_key_configured": agent_config["api_key_configured"],
        "api_key_prefix": agent_config["api_key_prefix"],
        "api_key_registered_at": agent_config["registered_at"],
        "api_center_online": api_health["online"],
        "api_center_message": api_health["message"],
        "heartbeat_interval_seconds": AGENT_HEARTBEAT_INTERVAL_SECONDS,
        "heartbeat_running": heartbeat_status["running"],
        "last_heartbeat_at": heartbeat_status.get("last_success") or heartbeat_status.get("last_success_at"),
        "last_heartbeat_error": heartbeat_status["last_error"],
        "api_key_api_center_url": heartbeat_status["api_key_api_center_url"],
        "api_key_url_matches": heartbeat_status["api_key_url_matches"],
    }


@app.post("/api/agent/api-center/retry")
async def agent_api_center_retry(current_admin: dict = Depends(get_current_admin)):
    """บังคับให้ Agent ลงทะเบียน key และส่ง heartbeat ใหม่ทันที"""
    try:
        result = _send_agent_heartbeat()
        with agent_heartbeat_lock:
            agent_heartbeat_state.update({
                "last_success": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "last_error": "",
            })
        return {"success": True, "message": "ลงทะเบียนและส่ง heartbeat สำเร็จ", "result": result}
    except Exception as exc:
        with agent_heartbeat_lock:
            agent_heartbeat_state["last_error"] = str(exc)
        return {"success": False, "message": f"ส่ง heartbeat ไม่สำเร็จ: {exc}"}


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
        status = _get_update_status(force=force)
        status["startup_auto_update"] = _get_startup_update_state()
        return status
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
    cache_key = None
    should_process = False
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

        content = await file.read()
        file_hash = hashlib.sha256(content).hexdigest()
        username = current_user.get("username", "")
        cache_key = f"{username}:{file.filename}:{len(content)}:{file_hash}"
        cached_upload = None

        with upload_cache_lock:
            cached_upload = recent_upload_cache.get(cache_key)
            if not cached_upload or time.time() - cached_upload.get("created_at", 0) > 10:
                cached_upload = {
                    "file_id": str(uuid.uuid4()),
                    "created_at": time.time(),
                    "status": "processing"
                }
                recent_upload_cache[cache_key] = cached_upload
                should_process = True

        if not should_process:
            for _ in range(150):
                cached_info = upload_store.get(cached_upload["file_id"])
                if cached_info:
                    return {
                        "success": True,
                        "file_id": cached_upload["file_id"],
                        "preview": cached_info["data"][:5],
                        "columns": cached_info["columns"],
                        "total_rows": cached_info["total_rows"],
                        "facilities": cached_info.get("facilities", []),
                        "duplicate": True
                    }
                await asyncio.sleep(0.1)

            return JSONResponse(
                status_code=409,
                content={
                    "success": False,
                    "message": "ไฟล์นี้กำลังอัปโหลดอยู่ กรุณารอสักครู่"
                }
            )

        file_id = cached_upload["file_id"]

        # บันทึกไฟล์
        os.makedirs(UPLOADS_DIR, exist_ok=True)
        file_ext = os.path.splitext(file.filename)[1]
        saved_filename = f"{file_id}{file_ext}"
        file_path = os.path.join(UPLOADS_DIR, saved_filename)

        with open(file_path, "wb") as buffer:
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

        recent_upload_cache[cache_key] = {
            "file_id": file_id,
            "created_at": time.time(),
            "status": "done"
        }
        cutoff = time.time() - 60
        for key, value in list(recent_upload_cache.items()):
            if value.get("created_at", 0) < cutoff:
                recent_upload_cache.pop(key, None)

        return {
            "success": True,
            "file_id": file_id,
            "preview": result["preview"],
            "columns": result["columns"],
            "total_rows": len(result["data"]),
            "facilities": result.get("facilities", [])
        }

    except Exception as e:
        if should_process and cache_key:
            with upload_cache_lock:
                recent_upload_cache.pop(cache_key, None)
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
        upload_store[file_id]["transformed_columns"] = result["columns"]
        upload_store[file_id]["output_path"] = output_path
        upload_store[file_id]["status"] = "completed"
        upload_store[file_id]["matched_count"] = result["matched_count"]
        upload_store[file_id]["unmatched_count"] = result["unmatched_count"]
        for count_key in ("pid_matched_count", "pid_unmatched_count", "cid_matched_count", "cid_unmatched_count"):
            upload_store[file_id][count_key] = result.get(count_key, 0)
        upload_store[file_id]["has_discharge"] = result.get("has_discharge", False)
        upload_store[file_id]["central_death_mismatch_count"] = result.get("central_death_mismatch_count", 0)
        upload_store[file_id]["central_death_lookup_available"] = result.get("central_death_lookup_available", True)
        upload_store[file_id]["central_death_lookup_message"] = result.get("central_death_lookup_message", "")
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
            "pid_matched_count": result.get("pid_matched_count", 0),
            "pid_unmatched_count": result.get("pid_unmatched_count", 0),
            "cid_matched_count": result.get("cid_matched_count", 0),
            "cid_unmatched_count": result.get("cid_unmatched_count", 0),
            "has_discharge": result.get("has_discharge", False),
            "central_death_mismatch_count": result.get("central_death_mismatch_count", 0),
            "central_death_lookup_available": result.get("central_death_lookup_available", True),
            "central_death_lookup_message": result.get("central_death_lookup_message", ""),
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


@app.get("/api/history/{file_id}")
async def get_history_detail(
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """ดึงรายละเอียดผลการแปลงข้อมูลเพื่อกลับมาดู/กรองในตารางได้"""
    if file_id not in upload_store:
        raise HTTPException(
            status_code=404,
            detail="ไม่พบข้อมูลประวัติที่ระบุ"
        )

    upload_info = upload_store[file_id]
    transformed_data = upload_info.get("transformed_data")
    if not transformed_data:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "รายการนี้ยังไม่มีผลการแปลงข้อมูล"
            }
        )

    transformed_columns = upload_info.get("transformed_columns")
    if not transformed_columns:
        transformed_columns = ["PERSON_CID", "FULL_NAME", "เงื่อนไขที่ใช้", "เทียบตาย"] + list(upload_info.get("columns", []))
    return {
        "success": True,
        "file_id": file_id,
        "filename": upload_info.get("original_filename", ""),
        "columns": transformed_columns,
        "data": transformed_data,
        "total_rows": len(transformed_data),
        "matched_count": upload_info.get("matched_count", 0),
        "unmatched_count": upload_info.get("unmatched_count", 0),
        "pid_matched_count": upload_info.get("pid_matched_count", 0),
        "pid_unmatched_count": upload_info.get("pid_unmatched_count", 0),
        "cid_matched_count": upload_info.get("cid_matched_count", 0),
        "cid_unmatched_count": upload_info.get("cid_unmatched_count", 0),
        "has_discharge": upload_info.get("has_discharge", False),
        "central_death_mismatch_count": upload_info.get("central_death_mismatch_count", 0),
        "central_death_lookup_available": upload_info.get("central_death_lookup_available", True),
        "central_death_lookup_message": upload_info.get("central_death_lookup_message", "")
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
    print(f"  🌐 URL: {APP_URL}")
    print(f"  📁 Uploads: {UPLOADS_DIR}")
    print("=" * 50)
    print()

    if _is_port_open(port=APP_PORT):
        if not SERVICE_MODE:
            webbrowser.open(APP_URL)
        sys.exit(0)

    # เปิด browser เฉพาะตอนผู้ใช้ดับเบิลคลิกเอง ไม่เปิดจาก Windows Startup task
    if not SERVICE_MODE:
        def open_browser():
            webbrowser.open(APP_URL)

        timer = threading.Timer(1.5, open_browser)
        timer.daemon = True
        timer.start()

    # เริ่ม server
    uvicorn.run(
        app,
        host=APP_HOST,
        port=APP_PORT,
        log_level="info"
    )
