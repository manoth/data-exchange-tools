"""Compatibility helpers for MariaDB/MySQL connections used by the Agent."""

import re
from typing import Any, Dict, Tuple

import pymysql
import pymysql.cursors


CHARSET_CANDIDATES = ("utf8mb4", "utf8")
CHARSET_ERROR_CODES = {1115, 1273, 2019}
READ_ONLY_UNSUPPORTED_CODES = {1064, 1193, 1231}


def parse_server_version(version: str) -> Tuple[int, ...]:
    """Parse MySQL/MariaDB versions, including the legacy 5.5.5- prefix."""
    value = str(version or "").strip()
    if value.startswith("5.5.5-") and "mariadb" in value.lower():
        value = value[6:]
    match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", value)
    if not match:
        return ()
    return tuple(int(part) for part in match.groups(default="0"))


def inspect_server(connection, connection_charset: str = "") -> Dict[str, Any]:
    """Return safe server/capability details without exposing credentials."""
    handshake_version = str(connection.get_server_info() or "")
    details = {
        "product": "MariaDB" if "mariadb" in handshake_version.lower() else "MySQL",
        "version": handshake_version,
        "version_tuple": list(parse_server_version(handshake_version)),
        "connection_charset": connection_charset,
        "server_charset": "",
        "server_collation": "",
    }
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT VERSION() AS version, "
                "@@version_comment AS version_comment, "
                "@@character_set_server AS server_charset, "
                "@@collation_server AS server_collation"
            )
            row = cursor.fetchone() or {}
        version = str(row.get("version") or handshake_version)
        comment = str(row.get("version_comment") or "")
        details.update({
            "product": "MariaDB" if "mariadb" in f"{version} {comment}".lower() else "MySQL",
            "version": version,
            "version_tuple": list(parse_server_version(version)),
            "server_charset": str(row.get("server_charset") or ""),
            "server_collation": str(row.get("server_collation") or ""),
        })
    except pymysql.MySQLError:
        # A successful handshake is enough. Very old/restricted servers may not
        # allow reading one or more system variables.
        pass
    return details


def _is_charset_error(error: BaseException) -> bool:
    code = error.args[0] if getattr(error, "args", ()) else 0
    message = " ".join(str(item) for item in getattr(error, "args", ())).lower()
    return (
        code in CHARSET_ERROR_CODES
        or "character set" in message
        or "charset" in message
        or "collation" in message
    )


def connect_compatible(
    config: Dict[str, Any],
    *,
    read_timeout: int = 30,
    write_timeout: int = 30,
    inspect: bool = True,
):
    """Connect using utf8mb4, falling back safely to utf8 for old servers."""
    last_error = None
    for charset in CHARSET_CANDIDATES:
        try:
            connection = pymysql.connect(
                host=config.get("host", "localhost"),
                port=int(config.get("port", 3306)),
                database=config.get("database", ""),
                user=config.get("username", ""),
                password=config.get("password", ""),
                charset=charset,
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=10,
                read_timeout=read_timeout,
                write_timeout=write_timeout,
                autocommit=False,
            )
            server = inspect_server(connection, charset) if inspect else {
                "product": "MariaDB" if "mariadb" in str(connection.get_server_info()).lower() else "MySQL",
                "version": str(connection.get_server_info() or ""),
                "version_tuple": list(parse_server_version(connection.get_server_info())),
                "connection_charset": charset,
                "server_charset": "",
                "server_collation": "",
            }
            return connection, server
        except pymysql.MySQLError as error:
            last_error = error
            if charset == "utf8mb4" and _is_charset_error(error):
                continue
            raise
    raise last_error or pymysql.err.OperationalError(2003, "Connection failed")


def start_read_only_transaction(connection) -> bool:
    """Start a read-only transaction, with a MariaDB 5-compatible fallback.

    Returns True when the server enforces READ ONLY and False when the Agent
    must rely on its existing SELECT-only SQL validation.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("START TRANSACTION READ ONLY")
        return True
    except pymysql.MySQLError as error:
        code = error.args[0] if error.args else 0
        if code not in READ_ONLY_UNSUPPORTED_CODES:
            raise
        connection.rollback()
        with connection.cursor() as cursor:
            cursor.execute("START TRANSACTION")
        return False


def database_error_message(error: BaseException, config: Dict[str, Any]) -> str:
    """Convert common connection errors to actionable Thai messages."""
    code = error.args[0] if getattr(error, "args", ()) else 0
    host = config.get("host", "localhost")
    port = config.get("port", 3306)
    database = config.get("database", "")
    messages = {
        1044: f"ผู้ใช้นี้ไม่มีสิทธิ์เข้าถึงฐานข้อมูล '{database}'",
        1045: "ชื่อผู้ใช้หรือรหัสผ่านฐานข้อมูลไม่ถูกต้อง",
        1049: f"ไม่พบฐานข้อมูล '{database}'",
        1130: f"เซิร์ฟเวอร์ฐานข้อมูลไม่อนุญาตให้เครื่องนี้เชื่อมต่อ (Host is not allowed)",
        1251: "รูปแบบยืนยันตัวตนของบัญชีฐานข้อมูลไม่รองรับ กรุณาใช้ mysql_native_password",
        2003: f"ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ {host}:{port} ได้ กรุณาตรวจสอบ host, port และ firewall",
        2026: "เชื่อมต่อ SSL/TLS ไม่สำเร็จ กรุณาตรวจสอบการตั้งค่าใบรับรองของเซิร์ฟเวอร์",
        2059: "ไม่สามารถโหลด authentication plugin ของบัญชีฐานข้อมูลได้ กรุณาใช้ mysql_native_password",
    }
    if code in messages:
        return messages[code]
    detail = str(error.args[1] if len(getattr(error, "args", ())) > 1 else error)
    return f"เชื่อมต่อฐานข้อมูลไม่สำเร็จ (รหัส {code or '-'}): {detail}"
