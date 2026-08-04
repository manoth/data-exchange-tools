"""Windows single-instance launcher and in-place service upgrade coordinator."""

import json
import os
import re
import shutil
import socket
import subprocess
import time
import urllib.request
import webbrowser
from pathlib import Path


PRODUCT_ID = "data-exchange-tools"
INSTALL_STATE_FILENAME = "installed.json"


def version_parts(version: str) -> tuple:
    parts = []
    for item in str(version or "").split("."):
        digits = "".join(char for char in item if char.isdigit())
        parts.append(int(digits or 0))
    return tuple((parts + [0, 0, 0])[:3])


def is_newer(candidate: str, current: str) -> bool:
    return version_parts(candidate) > version_parts(current)


def get_install_executable(environ=None) -> Path:
    environment = environ if environ is not None else os.environ
    local_app_data = environment.get("LOCALAPPDATA") or environment.get("APPDATA")
    if not local_app_data:
        raise RuntimeError("ไม่พบ LOCALAPPDATA สำหรับติดตั้ง service")
    return Path(local_app_data) / "Programs" / "DataExchangeTools" / "DataExchangeTools.exe"


def parse_legacy_frontend_version(html: str) -> str:
    if "Data Exchange Tools" not in html:
        return ""
    match = re.search(r"\bv(\d+\.\d+\.\d+)\b", html)
    return match.group(1) if match else ""


def _read_json_url(url: str, timeout: float = 1.2) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def probe_service(app_url: str) -> dict:
    """Recognize current releases and legacy releases without authentication."""
    try:
        runtime = _read_json_url(f"{app_url}/api/runtime")
        if runtime.get("product") == PRODUCT_ID:
            return {
                "running": True,
                "recognized": True,
                "version": str(runtime.get("version") or "0.0.0"),
                "pid": int(runtime.get("pid") or 0),
            }
    except Exception:
        pass

    try:
        with urllib.request.urlopen(f"{app_url}/", timeout=1.2) as response:
            html = response.read(256 * 1024).decode("utf-8", errors="ignore")
        version = parse_legacy_frontend_version(html)
        if version:
            return {"running": True, "recognized": True, "version": version, "pid": 0}
        return {"running": True, "recognized": False, "version": "", "pid": 0}
    except Exception:
        return {"running": False, "recognized": False, "version": "", "pid": 0}


def is_port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def parse_netstat_listener_pid(output: str, port: int) -> int:
    for raw_line in output.splitlines():
        columns = raw_line.split()
        if len(columns) < 5 or columns[0].upper() != "TCP" or columns[3].upper() != "LISTENING":
            continue
        local_address = columns[1]
        if local_address.rsplit(":", 1)[-1] == str(port) and columns[4].isdigit():
            return int(columns[4])
    return 0


def find_listener_pid(port: int) -> int:
    try:
        result = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return parse_netstat_listener_pid(result.stdout, port)
    except Exception:
        return 0


def _request_graceful_shutdown(app_url: str, data_dir: str):
    secret_path = Path(data_dir) / ".launcher_secret"
    try:
        launcher_secret = secret_path.read_text(encoding="utf-8").strip()
    except Exception:
        launcher_secret = ""
    headers = {"X-Launcher-Token": launcher_secret} if launcher_secret else {}
    request = urllib.request.Request(
        f"{app_url}/api/runtime/shutdown",
        data=b"",
        headers=headers,
        method="POST",
    )
    try:
        urllib.request.urlopen(request, timeout=2).read()
    except Exception:
        pass


def wait_for_port(port: int, expected_open: bool, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if is_port_open(port) == expected_open:
            return True
        time.sleep(0.25)
    return is_port_open(port) == expected_open


def wait_for_service(app_url: str, expected_version: str, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        service = probe_service(app_url)
        if service["recognized"] and not is_newer(expected_version, service["version"]):
            return True
        time.sleep(0.3)
    return False


def stop_service(app_url: str, port: int, data_dir: str, pid: int = 0) -> bool:
    _request_graceful_shutdown(app_url, data_dir)
    if wait_for_port(port, False, 5):
        return True

    process_id = pid or find_listener_pid(port)
    if not process_id:
        return False
    try:
        subprocess.run(
            ["taskkill", "/PID", str(process_id), "/T", "/F"],
            capture_output=True,
            timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        return False
    return wait_for_port(port, False, 10)


def _load_install_state(data_dir: str) -> dict:
    path = Path(data_dir) / INSTALL_STATE_FILENAME
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_install_state(data_dir: str, version: str, executable: Path, launcher: Path):
    directory = Path(data_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / INSTALL_STATE_FILENAME
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(
            {
                "version": version,
                "executable": str(executable),
                "launcher_path": str(launcher),
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    os.replace(str(temporary), str(path))


def register_launcher_path(data_dir: str, launcher: str):
    state = _load_install_state(data_dir)
    if not state:
        return
    state["launcher_path"] = str(Path(launcher).resolve())
    path = Path(data_dir) / INSTALL_STATE_FILENAME
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(str(temporary), str(path))


def cleanup_duplicate_desktop_shortcut(source_exe: str, app_url: str, environ=None):
    environment = environ if environ is not None else os.environ
    user_profile = environment.get("USERPROFILE")
    if not user_profile:
        return
    source_parent = os.path.normcase(os.path.abspath(os.path.dirname(source_exe)))
    candidates = [Path(user_profile) / "Desktop", Path(user_profile) / "OneDrive" / "Desktop"]
    for desktop in candidates:
        if source_parent != os.path.normcase(os.path.abspath(str(desktop))):
            continue
        shortcut = desktop / "Data Exchange Tools.url"
        try:
            content = shortcut.read_text(encoding="utf-8", errors="ignore")
            if content.startswith("[InternetShortcut]") and f"URL={app_url}" in content:
                shortcut.unlink()
        except OSError:
            pass


def prepare_service_executable(source_exe: str, current_version: str, data_dir: str) -> tuple[Path, str]:
    source = Path(source_exe).resolve()
    target = get_install_executable().resolve()
    state = _load_install_state(data_dir)
    installed_version = str(state.get("version") or "0.0.0")

    if target.is_file() and is_newer(installed_version, current_version):
        return target, installed_version

    target.parent.mkdir(parents=True, exist_ok=True)
    if source != target:
        temporary = target.with_suffix(".exe.new")
        shutil.copy2(source, temporary)
        os.replace(str(temporary), str(target))
    _save_install_state(data_dir, current_version, target, source)
    return target, current_version


def start_service(executable: Path):
    creation_flags = (
        getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        | getattr(subprocess, "DETACHED_PROCESS", 0)
        | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    )
    subprocess.Popen(
        [str(executable), "--service"],
        cwd=str(executable.parent),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags,
        close_fds=True,
    )


def show_error(message: str):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, "Data Exchange Tools", 0x10)
    except Exception:
        pass


def run_windows_launcher(current_version: str, app_url: str, port: int, data_dir: str, source_exe: str) -> int:
    cleanup_duplicate_desktop_shortcut(source_exe, app_url)
    running = probe_service(app_url)
    if not running["running"] and is_port_open(port):
        time.sleep(1)
        running = probe_service(app_url)
        if not running["running"]:
            show_error(f"Port {port} ถูกใช้งานแต่ไม่สามารถตรวจสอบ service ได้ กรุณาลองใหม่")
            return 1
    if running["running"] and not running["recognized"]:
        show_error(f"Port {port} ถูกใช้งานโดยโปรแกรมอื่น กรุณาปิดโปรแกรมนั้นก่อน")
        return 1

    if running["recognized"] and not is_newer(current_version, running["version"]):
        if version_parts(current_version) == version_parts(running["version"]):
            register_launcher_path(data_dir, source_exe)
        webbrowser.open(app_url)
        return 0

    if running["recognized"]:
        if not stop_service(app_url, port, data_dir, running.get("pid", 0)):
            show_error("ไม่สามารถปิด Data Exchange Tools รุ่นเดิมเพื่ออัปเดตได้")
            return 1

    try:
        service_exe, service_version = prepare_service_executable(source_exe, current_version, data_dir)
        start_service(service_exe)
    except Exception as exc:
        show_error(f"ไม่สามารถติดตั้งหรือเปิด service ได้: {exc}")
        return 1

    if not wait_for_service(app_url, service_version, 25):
        show_error("เปิด Data Exchange Tools service ไม่สำเร็จ กรุณาตรวจ update.log")
        return 1

    webbrowser.open(app_url)
    return 0
