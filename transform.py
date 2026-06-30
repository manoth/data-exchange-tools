"""
Transform Module - แปลงข้อมูล Excel
อ่านไฟล์ Excel, แปลงข้อมูลโดยจับคู่กับฐานข้อมูล, ส่งออกเป็น Excel ใหม่
"""

import os
from datetime import datetime
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from database import get_connection
from config import APP_DIR

# กำหนด path สำหรับไฟล์อัพโหลด
UPLOADS_DIR = os.path.join(APP_DIR, "uploads")


def _cell_to_text(value) -> str:
    """แปลงค่า cell เป็น text โดยรักษารหัสที่มีศูนย์นำหน้าเท่าที่ openpyxl ส่งมาได้"""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _normalize_pid(value) -> str:
    """Normalize pid สำหรับเทียบกับ person.person_id โดยไม่บังคับตัดศูนย์นำหน้า"""
    text = _cell_to_text(value)
    if not text:
        return ""
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    return text


def _normalize_hoscode(value) -> str:
    """Normalize hospital code จาก opdconfig/excel ให้เทียบกันตรงที่สุด"""
    text = _cell_to_text(value).strip().strip('"').strip("'")
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    return text


def _normalize_column_name(value, index: int) -> str:
    text = _cell_to_text(value) if value is not None else ""
    return (text or f"COLUMN_{index + 1}").strip().upper()


def _make_unique_columns(raw_columns: list) -> list:
    columns = []
    seen = {}
    for index, cell in enumerate(raw_columns):
        base_name = _normalize_column_name(cell, index)
        count = seen.get(base_name, 0) + 1
        seen[base_name] = count
        columns.append(base_name if count == 1 else f"{base_name}_{count}")
    return columns


def _extract_facilities(data: list) -> list:
    facilities = {}
    for row in data:
        hoscode = _cell_to_text(row.get("HOSCODE", ""))
        if not hoscode:
            continue
        hosname = _cell_to_text(row.get("HOSNAME", ""))
        item = facilities.setdefault(hoscode, {"hoscode": hoscode, "hosname": hosname, "rows": 0})
        item["rows"] += 1
        if hosname and not item.get("hosname"):
            item["hosname"] = hosname
    return sorted(facilities.values(), key=lambda item: (item["hoscode"], item["hosname"]))


def _chunks(values: list, size: int = 800):
    for index in range(0, len(values), size):
        yield values[index:index + size]


def process_upload(file_path: str) -> dict:
    """
    อ่านไฟล์ Excel และส่งคืนข้อมูล columns, data, preview

    Args:
        file_path: path ไปยังไฟล์ Excel

    Returns:
        dict: {columns, data, preview}
    """
    try:
        # อ่านไฟล์ Excel (read_only=True สำหรับไฟล์ขนาดใหญ่)
        wb = load_workbook(file_path, read_only=True, data_only=True)

        # ใช้ sheet ชื่อ 'Data' หรือ sheet แรก
        if "Data" in wb.sheetnames:
            ws = wb["Data"]
        else:
            ws = wb.active

        # อ่าน header จากแถวแรก
        columns = []
        rows_data = []

        for row_idx, row in enumerate(ws.iter_rows(values_only=True)):
            if row_idx == 0:
                # แถวแรกเป็น header
                columns = _make_unique_columns(list(row))
            else:
                # แถวข้อมูล
                row_dict = {}
                for col_idx, cell in enumerate(row):
                    if col_idx < len(columns):
                        col_name = columns[col_idx]
                        row_dict[col_name] = _cell_to_text(cell)
                # ข้ามแถวว่าง
                if any(v != "" and v is not None for v in row_dict.values()):
                    rows_data.append(row_dict)

        wb.close()

        # สร้าง preview (5 แถวแรก)
        preview = rows_data[:5]

        return {
            "columns": columns,
            "data": rows_data,
            "preview": preview,
            "facilities": _extract_facilities(rows_data)
        }

    except Exception as e:
        raise Exception(f"เกิดข้อผิดพลาดในการอ่านไฟล์ Excel: {e}")


def transform_data(file_id: str, data: list, columns: list, selected_hoscodes: list = None) -> dict:
    """
    แปลงข้อมูลโดยจับคู่ pid กับตาราง person

    Args:
        file_id: ID ของไฟล์
        data: list ของ dict ข้อมูลจาก Excel
        columns: list ของชื่อคอลัมน์

    Returns:
        dict: {data, columns, matched_count, unmatched_count}
    """
    try:
        father_column = next((col for col in columns if str(col).upper() == "FATHER"), None)
        mother_column = next((col for col in columns if str(col).upper() == "MOTHER"), None)
        has_father_column = father_column is not None
        has_mother_column = mother_column is not None
        person_columns = ["PERSON_CID", "FULL_NAME"]

        selected_hoscodes = [str(code).strip() for code in (selected_hoscodes or []) if str(code).strip()]
        if selected_hoscodes:
            selected_set = {_normalize_hoscode(code) for code in selected_hoscodes}
            data = [row for row in data if _normalize_hoscode(row.get("HOSCODE", "")) in selected_set]

        def empty_person_fields() -> dict:
            fields = {
                "PERSON_CID": "",
                "FULL_NAME": "",
                "_matched": False,
            }
            return fields

        def apply_person_fields(target: dict, person: dict) -> None:
            target["PERSON_CID"] = person.get("cid", "")
            target["FULL_NAME"] = person.get("full_name", "")
            if father_column and person.get("father_name"):
                target[father_column] = person.get("father_name", "")
            if mother_column and person.get("mother_name"):
                target[mother_column] = person.get("mother_name", "")
            target["_matched"] = True

        # ค้นหาคอลัมน์ pid (ไม่สนใจตัวพิมพ์เล็ก/ใหญ่)
        pid_column = None
        hoscode_column = None
        for col in columns:
            if col.lower() == "pid":
                pid_column = col
            if col.lower() == "hoscode":
                hoscode_column = col

        if pid_column is None or hoscode_column is None:
            transformed_data = []
            for row in data:
                new_row = dict(row)
                new_row.update(empty_person_fields())
                transformed_data.append(new_row)
            return {
                "data": transformed_data,
                "columns": person_columns + columns,
                "matched_count": 0,
                "unmatched_count": len(data)
            }

        # ดึงค่า pid ทั้งหมดจากข้อมูล โดยเก็บทั้งแบบเดิมและแบบตัดศูนย์นำหน้า
        pid_lookup_keys = set()
        for row in data:
            pid_str = _normalize_pid(row.get(pid_column, ""))
            if pid_str:
                pid_lookup_keys.add(pid_str)
                if pid_str.isdigit():
                    pid_lookup_keys.add(str(int(pid_str)))

        pid_values = sorted(pid_lookup_keys)

        if not pid_values:
            transformed_data = []
            for row in data:
                new_row = dict(row)
                new_row.update(empty_person_fields())
                transformed_data.append(new_row)
            return {
                "data": transformed_data,
                "columns": person_columns + columns,
                "matched_count": 0,
                "unmatched_count": len(data)
            }

        # Query ข้อมูลจากตาราง person แบบ batch เพื่อไม่ให้ IN clause ใหญ่เกินไป
        results = []
        local_hoscodes = set()
        connection = None
        try:
            connection = get_connection()
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT hospitalcode
                    FROM opdconfig
                    WHERE hospitalcode IS NOT NULL AND hospitalcode <> ''
                """)
                local_hoscodes = {
                    _normalize_hoscode(row.get("hospitalcode"))
                    for row in cursor.fetchall()
                    if _normalize_hoscode(row.get("hospitalcode"))
                }

                for batch in _chunks(pid_values):
                    placeholders = ",".join(["%s"] * len(batch))
                    sql = f"""
                        SELECT
                            person_id,
                            cid,
                            pname,
                            fname,
                            lname,
                            father_name,
                            mother_name
                        FROM person
                        WHERE CAST(person_id AS CHAR) IN ({placeholders})
                    """
                    cursor.execute(sql, tuple(batch))
                    results.extend(cursor.fetchall())
        finally:
            if connection:
                connection.close()

        # สร้าง mapping: person_id -> {cid, full_name}
        person_map = {}
        for row in results:
            person_id = _normalize_pid(row.get("person_id"))
            person = {
                "cid": row.get("cid", ""),
                "full_name": "".join([
                    str(row.get("pname") or ""),
                    str(row.get("fname") or ""),
                    " ",
                    str(row.get("lname") or ""),
                ]).strip(),
                "father_name": row.get("father_name", "") or "",
                "mother_name": row.get("mother_name", "") or "",
            }
            person_map[person_id] = person
            if person_id.isdigit():
                person_map[str(int(person_id))] = person

        # แปลงข้อมูล
        matched_count = 0
        unmatched_count = 0
        transformed_data = []

        for row in data:
            new_row = dict(row)
            pid_str = _normalize_pid(row.get(pid_column, ""))
            row_hoscode = _normalize_hoscode(row.get(hoscode_column, ""))
            hoscode_matched = bool(row_hoscode and row_hoscode in local_hoscodes)

            if pid_str and hoscode_matched:
                lookup_keys = [pid_str]
                if pid_str.isdigit():
                    lookup_keys.append(str(int(pid_str)))
                person = next((person_map[key] for key in lookup_keys if key in person_map), None)
                if person:
                    apply_person_fields(new_row, person)
                    matched_count += 1
                else:
                    new_row.update(empty_person_fields())
                    unmatched_count += 1
            else:
                new_row.update(empty_person_fields())
                unmatched_count += 1

            transformed_data.append(new_row)

        return {
            "data": transformed_data,
            "columns": person_columns + columns,
            "matched_count": matched_count,
            "unmatched_count": unmatched_count
        }

    except Exception as e:
        raise Exception(f"เกิดข้อผิดพลาดในการแปลงข้อมูล: {e}")


def export_excel(data: list, columns: list, original_filename: str) -> str:
    """
    ส่งออกข้อมูลที่แปลงแล้วเป็นไฟล์ Excel ใหม่

    Args:
        data: list ของ dict ข้อมูลที่แปลงแล้ว
        columns: list ของชื่อคอลัมน์
        original_filename: ชื่อไฟล์ต้นฉบับ

    Returns:
        str: path ไปยังไฟล์ Excel ที่สร้าง
    """
    try:
        # สร้างโฟลเดอร์ uploads หากยังไม่มี
        os.makedirs(UPLOADS_DIR, exist_ok=True)

        # สร้าง workbook ใหม่
        wb = Workbook()
        ws = wb.active
        ws.title = "Data"

        # กำหนด style สำหรับ header
        header_font = Font(name="TH SarabunPSK", size=14, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="2E86AB", end_color="2E86AB", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin")
        )

        export_columns = [col for col in columns if not str(col).startswith("_")]

        # เขียน header
        for col_idx, col_name in enumerate(export_columns, 1):
            cell = ws.cell(row=1, column=col_idx, value=col_name)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border

        # กำหนด style สำหรับ data
        data_font = Font(name="TH SarabunPSK", size=14)
        data_alignment = Alignment(vertical="center")

        # เขียนข้อมูล
        for row_idx, row_data in enumerate(data, 2):
            for col_idx, col_name in enumerate(export_columns, 1):
                value = row_data.get(col_name, "")
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.font = data_font
                cell.alignment = data_alignment
                cell.border = thin_border

        # Auto-size columns
        for col_idx, col_name in enumerate(export_columns, 1):
            max_length = len(str(col_name))
            for row in ws.iter_rows(min_row=2, min_col=col_idx, max_col=col_idx):
                for cell in row:
                    try:
                        cell_length = len(str(cell.value)) if cell.value else 0
                        if cell_length > max_length:
                            max_length = cell_length
                    except Exception:
                        pass
            # กำหนดความกว้างคอลัมน์ (เพิ่ม padding)
            adjusted_width = min(max_length + 4, 50)
            ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = adjusted_width

        # ตั้งแถวแรกเป็น freeze pane
        ws.freeze_panes = "A2"

        # สร้างชื่อไฟล์ output
        name_without_ext = os.path.splitext(original_filename)[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{name_without_ext}_completed_{timestamp}.xlsx"
        output_path = os.path.join(UPLOADS_DIR, output_filename)

        # บันทึกไฟล์
        wb.save(output_path)
        wb.close()

        return output_path

    except Exception as e:
        raise Exception(f"เกิดข้อผิดพลาดในการส่งออกไฟล์ Excel: {e}")
