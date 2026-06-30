from pathlib import Path
from datetime import datetime
from html import escape
import shutil

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
MANUAL_DIR = ROOT / "คู่มือ"
IMG_DIR = MANUAL_DIR / "images" / "manual-web"
OUT_HTML = MANUAL_DIR / "manual.html"
STATIC_MANUAL_HTML = ROOT / "static" / "manual.html"
STATIC_MANUAL_FRAGMENT = ROOT / "static" / "manual_fragment.html"
STATIC_IMG_DIR = ROOT / "static" / "images" / "manual"

FONT_REG = "/Library/Fonts/THSarabun.ttf"
FONT_BOLD = "/Library/Fonts/THSarabun Bold.ttf"


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def wrap_text(draw, text, font_obj, max_width):
    lines = []
    for raw_line in text.splitlines():
        words = raw_line.split(" ")
        line = ""
        for word in words:
            candidate = word if not line else f"{line} {word}"
            width = draw.textbbox((0, 0), candidate, font=font_obj)[2]
            if width <= max_width:
                line = candidate
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)
    return lines


def draw_wrapped(draw, xy, text, font_obj, fill, max_width, line_gap=6):
    x, y = xy
    for line in wrap_text(draw, text, font_obj, max_width):
        draw.text((x, y), line, font=font_obj, fill=fill)
        y += draw.textbbox((0, 0), line, font=font_obj)[3] + line_gap
    return y


def draw_centered_wrapped(draw, box, text, font_obj, fill, line_gap=6):
    x1, y1, x2, y2 = box
    lines = wrap_text(draw, text, font_obj, x2 - x1)
    line_heights = [draw.textbbox((0, 0), line, font=font_obj)[3] for line in lines]
    total_h = sum(line_heights) + max(0, len(lines) - 1) * line_gap
    y = y1 + max(0, (y2 - y1 - total_h) / 2)
    for line, line_h in zip(lines, line_heights):
        w = draw.textbbox((0, 0), line, font=font_obj)[2]
        draw.text((x1 + (x2 - x1 - w) / 2, y), line, font=font_obj, fill=fill)
        y += line_h + line_gap


def make_workflow_image():
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    out = IMG_DIR / "00-workflow.png"
    w, h = 1700, 980
    img = Image.new("RGB", (w, h), "#F5F8FC")
    draw = ImageDraw.Draw(img)
    title = font(FONT_BOLD, 58)
    box_title = font(FONT_BOLD, 34)
    body = font(FONT_REG, 28)
    small = font(FONT_REG, 25)

    draw.rounded_rectangle((38, 38, w - 38, h - 38), radius=28, fill="#FFFFFF", outline="#C8D8EA", width=3)
    draw.rectangle((38, 38, w - 38, 150), fill="#E8F0FA")
    draw.text((80, 62), "Flow การทำงานของ Data Exchange Tools", font=title, fill="#1F4D78")
    draw.text((82, 118), "ภาพรวมตั้งแต่ Login, Upload Excel, ตรวจหน่วยบริการ, Join PERSON และ Export Excel", font=small, fill="#5D7287")

    boxes = [
        (110, 235, 500, 430, "1. Login", "ผู้ใช้เข้าใช้งานผ่านบัญชี HOSxP หรือ admin สำหรับตั้งค่าระบบ"),
        (655, 235, 1045, 430, "2. Upload Excel", "เลือกไฟล์ Exchange .xlsx ที่ดาวน์โหลดจาก HDC"),
        (1200, 235, 1590, 430, "3. เลือกหน่วยบริการ", "กรองด้วย HOSCODE/HOSNAME หรือเลือกทั้งหมด"),
        (110, 615, 500, 810, "4. ตรวจ HOSCODE", "เทียบ Excel.HOSCODE กับ opdconfig.hospitalcode ของหน่วยบริการ"),
        (655, 615, 1045, 810, "5. Join PERSON", "LEFT JOIN ด้วย PID กับ person.person_id แล้วเติม CID และ FULL_NAME"),
        (1200, 615, 1590, 810, "6. ดูผล/Export", "กรองตาราง ดูย้อนหลัง และส่งออก Excel"),
    ]
    for x1, y1, x2, y2, head, desc in boxes:
        draw.rounded_rectangle((x1 + 5, y1 + 7, x2 + 5, y2 + 7), radius=22, fill="#D9E7F4")
        draw.rounded_rectangle((x1, y1, x2, y2), radius=22, fill="#FFFFFF", outline="#2E74B5", width=3)
        draw.rectangle((x1, y1, x2, y1 + 58), fill="#EAF2FB")
        draw.text((x1 + 24, y1 + 12), head, font=box_title, fill="#1F4D78")
        draw_centered_wrapped(draw, (x1 + 28, y1 + 70, x2 - 28, y2 - 22), desc, body, "#243B53", line_gap=8)

    arrows = [((520, 332), (635, 332)), ((1065, 332), (1180, 332)), ((1395, 452), (1395, 590)), ((1180, 712), (1065, 712)), ((635, 712), (520, 712))]
    for (sx, sy), (ex, ey) in arrows:
        draw.line((sx, sy, ex, ey), fill="#43A047", width=8)
        if ex > sx:
            pts = [(ex, ey), (ex - 24, ey - 16), (ex - 24, ey + 16)]
        elif ex < sx:
            pts = [(ex, ey), (ex + 24, ey - 16), (ex + 24, ey + 16)]
        else:
            pts = [(ex, ey), (ex - 16, ey - 24), (ex + 16, ey - 24)]
        draw.polygon(pts, fill="#43A047")

    draw.rounded_rectangle((110, 870, 1590, 925), radius=16, fill="#FFF8E1", outline="#F2C94C", width=2)
    draw_centered_wrapped(draw, (140, 876, 1560, 922), "หลักสำคัญ: ตารางผลลัพธ์ใช้ column จากไฟล์ Excel เป็นฐาน และเติมข้อมูลจริงจาก PERSON ตามเงื่อนไข HOSCODE + PID", small, "#5A4500", line_gap=3)
    img.save(out, quality=92)
    return out.name


def make_update_image():
    out = IMG_DIR / "08-update-flow.png"
    w, h = 1500, 760
    img = Image.new("RGB", (w, h), "#F6FAFB")
    draw = ImageDraw.Draw(img)
    title = font(FONT_BOLD, 58)
    head = font(FONT_BOLD, 36)
    body = font(FONT_REG, 30)
    draw.text((70, 55), "ขั้นตอน Update Online", font=title, fill="#0B2545")
    steps = [
        ("1", "ผู้ดูแลระบบกดเช็ก Update", "ระบบอ่าน latest.json จาก GitHub Release"),
        ("2", "พบเวอร์ชันใหม่", "แสดงปุ่ม Update เมื่อ version สูงกว่าเครื่อง client"),
        ("3", "ดาวน์โหลดไฟล์หน้าเว็บ", "ตรวจ SHA256 ก่อนแตกไฟล์ลงโฟลเดอร์ static"),
        ("4", "Refresh หน้าเว็บ", "หน้าเว็บและฟังก์ชัน frontend เปลี่ยนตามเวอร์ชันใหม่"),
    ]
    x = 70
    for number, htxt, btxt in steps:
        draw.rounded_rectangle((x, 170, x + 320, 560), radius=28, fill="#FFFFFF", outline="#2E86AB", width=3)
        draw.ellipse((x + 28, 205, x + 98, 275), fill="#38C8D8")
        draw.text((x + 52, 215), number, font=head, fill="#FFFFFF")
        draw_wrapped(draw, (x + 28, 305), htxt, head, "#1F4D78", 265)
        draw_wrapped(draw, (x + 28, 410), btxt, body, "#334155", 265)
        if number != "4":
            draw.line((x + 330, 365, x + 385, 365), fill="#5FD18A", width=7)
            draw.polygon([(x + 385, 365), (x + 365, 352), (x + 365, 378)], fill="#5FD18A")
        x += 360
    draw_wrapped(draw, (70, 625), "หมายเหตุ: ถ้าเป็นการแก้เฉพาะ frontend ไม่ต้อง build exe ใหม่ client สามารถกด Update จากหน้าเว็บได้", body, "#0F5132", 1320)
    img.save(out, quality=92)
    return out.name


def make_install_image():
    out = IMG_DIR / "09-install-windows.png"
    w, h = 1500, 760
    img = Image.new("RGB", (w, h), "#061F24")
    draw = ImageDraw.Draw(img)
    title = font(FONT_BOLD, 58)
    head = font(FONT_BOLD, 36)
    body = font(FONT_REG, 31)
    draw.text((70, 55), "ติดตั้งและเปิดใช้งานบน Windows", font=title, fill="#EAF7F4")
    cards = [
        ("วางโฟลเดอร์โปรแกรม", "แตกไฟล์หรือคัดลอกโฟลเดอร์ dist ไปไว้ในเครื่อง client"),
        ("ดับเบิลคลิก .exe", "เปิด DataExchangeTools.exe เพื่อเริ่ม service และเช็ก update ล่าสุด"),
        ("Auto Startup", "ระบบสร้าง Scheduled Task ให้ service เริ่มเองเมื่อ login Windows"),
        ("Desktop Shortcut", "กด shortcut Data Exchange Tools เมื่อต้องการเปิดหน้าเว็บใช้งาน"),
    ]
    x = 70
    for i, (htext, btext) in enumerate(cards, 1):
        draw.rounded_rectangle((x, 180, x + 320, 565), radius=28, fill="#0E343B", outline="#2C6768", width=3)
        draw.text((x + 32, 220), f"{i:02d}", font=font(FONT_BOLD, 62), fill="#62D989")
        draw_wrapped(draw, (x + 32, 315), htext, head, "#5FE0E9", 260)
        draw_wrapped(draw, (x + 32, 420), btext, body, "#D9ECE8", 260)
        x += 355
    draw.rounded_rectangle((70, 625, 1430, 690), radius=20, fill="#123D3E", outline="#2C6768")
    draw_wrapped(draw, (105, 630), "Startup task จะรันแบบไม่เปิด browser อัตโนมัติ ส่วน shortcut บน Desktop ใช้เปิดหน้าเว็บเมื่อผู้ใช้ต้องการเข้าใช้งาน", body, "#EAF7F4", 1260)
    img.save(out, quality=92)
    return out.name


def image_tag(filename, caption):
    path = IMG_DIR / filename
    if not path.exists():
        return ""
    return f"""
    <figure class="shot">
      <img src="/manual/assets/{escape(filename)}" alt="{escape(caption)}">
      <figcaption>{escape(caption)}</figcaption>
    </figure>
    """


def manual_body(now):
    return f"""
      <section class="manual-hero" id="overview">
        <p class="manual-eyebrow">Data Exchange Tools</p>
        <h1>คู่มือการทำงานและวิธีใช้งานระบบ</h1>
        <p class="manual-lead">คู่มือนี้จัดทำเป็นหน้าเว็บภายในระบบ เพื่อให้ผู้ใช้งานเปิดอ่านจากหน้า Login หรือเมนู “คู่มือการใช้งาน” ได้ทันที</p>
        <div class="manual-note warning">
          <strong>ข้อควรระวังด้านความปลอดภัย:</strong> คู่มือนี้ไม่แสดงรหัสผ่านจริง ไม่ควรส่งต่อรหัสผ่าน admin หรือรหัสผ่านฐานข้อมูลผ่านเอกสาร/ภาพหน้าจอ ให้ส่งแยกเฉพาะผู้มีสิทธิ์เท่านั้น
        </div>
      </section>

      {image_tag("00-workflow.png", "Flow การทำงานโดยรวมของระบบ")}

      <section class="manual-section" id="install">
        <h2>ติดตั้งและเปิดใช้งานบน Windows</h2>
        {image_tag("09-install-windows.png", "ขั้นตอนติดตั้งและเปิดใช้งานบน Windows")}
        <ol>
          <li>นำโฟลเดอร์โปรแกรมที่ build แล้วไปไว้ในเครื่อง client ของหน่วยบริการ</li>
          <li>ดับเบิลคลิก <code>DataExchangeTools.exe</code> เพื่อเปิด service เว็บ ระบบจะเช็ก update ล่าสุดจาก GitHub Release อัตโนมัติ</li>
          <li>ระบบจะสร้าง Windows Scheduled Task สำหรับเปิด service อัตโนมัติเมื่อ login Windows โดยไม่เปิด browser ขึ้นมาเอง</li>
          <li>ระบบจะสร้าง shortcut บน Desktop สำหรับเปิด <code>http://localhost:8899</code> เมื่อต้องการเข้าใช้งาน</li>
          <li>ถ้าเปิดไม่ได้ให้ตรวจสอบว่า port <code>8899</code> ว่าง และ antivirus/firewall ไม่บล็อกโปรแกรม</li>
        </ol>
      </section>

      <section class="manual-section" id="first-admin">
        <h2>เข้าใช้งานครั้งแรกและส่วนของ Admin</h2>
        {image_tag("01-login.png", "หน้า Login ของระบบ")}
        <h3>ลำดับบังคับสำหรับการเปิดใช้งานครั้งแรก</h3>
        <ol>
          <li>เข้าสู่ระบบด้วยบัญชีผู้ดูแลระบบเริ่มต้น <code>admin</code> และรหัสผ่านเริ่มต้น <code>admin</code></li>
          <li>ระบบจะพาไปหน้าเปลี่ยนรหัสผ่านผู้ดูแลระบบทันที ผู้ดูแลระบบต้องตั้งรหัสผ่านใหม่ก่อนใช้งานต่อ</li>
          <li>รหัสผ่านใหม่ต้องไม่ซ้ำกับรหัสผ่านเดิม มีอย่างน้อย 8 ตัวอักษร และมีตัวพิมพ์เล็ก ตัวพิมพ์ใหญ่ ตัวเลข และอักขระพิเศษ</li>
          <li>เมื่อเปลี่ยนรหัสผ่านสำเร็จ ระบบจะบังคับให้ตั้งค่าการเชื่อมต่อฐานข้อมูล HIS/HosXP ของหน่วยบริการ</li>
          <li>ต้องกด “ทดสอบการเชื่อมต่อ” ให้สำเร็จก่อน จึงจะบันทึกการตั้งค่าและเริ่มใช้งานระบบได้</li>
        </ol>
        {image_tag("02-admin-change-password.png", "หลัง Login ครั้งแรก ระบบบังคับให้เปลี่ยนรหัสผ่าน admin")}
        {image_tag("03-first-db-config.png", "หลังเปลี่ยนรหัสผ่าน ระบบบังคับให้ตั้งค่าการเชื่อมต่อฐานข้อมูล HIS/HosXP")}
        <h3>การตั้งค่าฐานข้อมูลครั้งแรก</h3>
        <p>เมื่อมาถึงหน้าตั้งค่าฐานข้อมูล ให้กรอก Host, Port, Database, Username และ Password ของฐานข้อมูล HIS/HosXP ของหน่วยบริการ จากนั้นต้องกด “ทดสอบการเชื่อมต่อ” ก่อนบันทึกทุกครั้ง</p>
        {image_tag("03-first-db-config-filled.png", "กรอกข้อมูลเชื่อมต่อฐานข้อมูล โดยช่อง Password แสดงแบบปิดรหัส")}
        {image_tag("03-first-db-config-test-failed.png", "ตัวอย่างกรณีทดสอบการเชื่อมต่อไม่สำเร็จ ระบบแสดง popup แจ้งเตือนชัดเจน")}
        {image_tag("03-first-db-config-test-success.png", "ตัวอย่างกรณีทดสอบการเชื่อมต่อสำเร็จ ระบบแจ้งว่าสามารถบันทึกการตั้งค่าได้")}
        {image_tag("03-first-db-config-saved-upload.png", "เมื่อบันทึกการตั้งค่าสำเร็จ ระบบจะพาไปหน้าอัปโหลดไฟล์ Exchange")}
        <div class="manual-grid">
          <div class="manual-card">
            <div class="manual-step-title">บัญชี admin ใช้ทำอะไร</div>
            <p>admin ใช้สำหรับตั้งค่าฐานข้อมูล ตรวจ update ปิด service และจัดการส่วนที่ผู้ใช้ทั่วไปไม่ควรเข้าถึง</p>
          </div>
          <div class="manual-card">
            <div class="manual-step-title">หลังตั้งค่าครั้งแรก</div>
            <p>เมื่อฐานข้อมูลเชื่อมต่อสำเร็จ ผู้ใช้ทั่วไปจะ Login ด้วยบัญชีจากตาราง <code>opduser</code> ของ HosXP ได้</p>
          </div>
        </div>
        {image_tag("07-config.png", "หน้าตั้งค่าการเชื่อมต่อฐานข้อมูลสำหรับ admin")}
        <div class="manual-note success">
          ถ้ายังไม่ทดสอบการเชื่อมต่อ หรือทดสอบไม่สำเร็จ ระบบจะไม่ให้บันทึกการตั้งค่า เพื่อป้องกันการใช้งานด้วย config ที่ผิด และถ้ามีการแก้ไขค่าใดหลังทดสอบผ่าน ต้องทดสอบใหม่ก่อนบันทึกอีกครั้ง
        </div>
      </section>

      <section class="manual-section" id="normal-use">
        <h2>การใช้งานโปรแกรมแบบปกติ</h2>
        {image_tag("02-upload-empty.png", "หน้าอัปโหลดไฟล์ Exchange")}
        <h3>ขั้นตอนอัปโหลดและแปลงข้อมูล</h3>
        <ol>
          <li>เข้าเมนู “อัปโหลด & แปลงข้อมูล”</li>
          <li>เลือกไฟล์ Exchange นามสกุล <code>.xlsx</code> ที่ดาวน์โหลดจาก HDC</li>
          <li>ตรวจสอบตัวอย่างข้อมูล 5 แถวแรก</li>
          <li>เลือกหน่วยบริการจาก HOSCODE/HOSNAME หรือเลือก “ทั้งหมด”</li>
          <li>กด “แปลงข้อมูล” ระบบจะนำ PID และ HOSCODE ไปตรวจร่วมกับฐานข้อมูล HIS</li>
          <li>ตรวจผลลัพธ์ในตาราง กรอง/ค้นหาได้ และกด “ส่งออก Excel” เมื่อต้องการไฟล์ผลลัพธ์</li>
        </ol>
        {image_tag("04-results-detail.png", "หน้าตารางผลลัพธ์หลังแปลงข้อมูล สามารถค้นหา กรอง และส่งออก Excel ได้")}
      </section>

      <section class="manual-section" id="history">
        <h2>ประวัติการแปลงและการกลับมาดูรายละเอียด</h2>
        {image_tag("05-history.png", "หน้าประวัติการแปลงข้อมูล")}
        <p>เมนูประวัติช่วยให้กลับมาดาวน์โหลดไฟล์ที่เคยแปลงสำเร็จ หรือกด “ดูรายละเอียด” เพื่อเปิดตารางผลลัพธ์เดิมกลับมาค้นหา/กรองซ้ำได้</p>
      </section>

      <section class="manual-section" id="update">
        <h2>Update โปรแกรม</h2>
        {image_tag("06-settings-update.png", "หน้า Settings สำหรับตรวจสอบและกด Update")}
        {image_tag("08-update-flow.png", "Flow การ Update Online ผ่าน GitHub Release")}
        <ol>
          <li>เมื่อ service เริ่มทำงาน ระบบจะเช็ก update จาก GitHub Release ให้อัตโนมัติหนึ่งครั้ง</li>
          <li>ถ้าเป็น Windows .exe update ระบบจะดาวน์โหลด ตรวจ SHA256 แทนที่ไฟล์ .exe และ restart service เพื่อใช้เวอร์ชันใหม่</li>
          <li>ถ้าเป็น frontend update ระบบจะดาวน์โหลด ตรวจ SHA256 และติดตั้งลงโฟลเดอร์ static ให้อัตโนมัติ</li>
          <li>ผู้ดูแลระบบยังสามารถเข้าสู่ระบบด้วย admin ไปที่เมนู “ตั้งค่า” แล้วกด “เช็ก Update” เพื่อตรวจซ้ำได้</li>
          <li>ถ้ามีเวอร์ชันใหม่ที่ต้อง update ด้วยมือ ระบบจะแสดงปุ่มให้กด Update</li>
          <li>เมื่อ update เฉพาะ frontend สำเร็จ ให้ refresh browser หนึ่งครั้ง</li>
        </ol>
      </section>

      <section class="manual-section" id="troubleshoot">
        <h2>แก้ปัญหาเบื้องต้น</h2>
        <div class="manual-card">
          <h3>Login ไม่ได้</h3>
          <p>ตรวจสอบว่าตั้งค่าฐานข้อมูลสำเร็จแล้ว และบัญชีผู้ใช้มีอยู่ในตาราง <code>opduser</code> ของ HosXP</p>
        </div>
        <div class="manual-card">
          <h3>แปลงแล้วจับคู่ไม่ได้</h3>
          <p>ตรวจสอบว่า Excel มี column <code>HOSCODE</code> และ <code>PID</code> ถูกต้อง โดยระบบจะตรวจ HOSCODE กับ <code>opdconfig.hospitalcode</code> และตรวจ PID กับ <code>person.person_id</code></p>
        </div>
        <div class="manual-card">
          <h3>Update ไม่ขึ้น</h3>
          <p>ตรวจสอบ internet ของเครื่อง client, GitHub Release ล่าสุดต้องมี <code>latest.json</code> และไฟล์ update ต้องมีค่า SHA256 ตรงกับ manifest</p>
        </div>
      </section>

      <footer class="manual-footer">
        คู่มือนี้สร้างจากภาพหน้าจอจริงของระบบและ infographic ที่สร้างขึ้นสำหรับอธิบายขั้นตอนการทำงาน · อัปเดตล่าสุด {escape(now)}
      </footer>
"""


def manual_css(scope=".manual-document"):
    return f"""
    {scope} {{
      --manual-blue: #1F4D78;
      --manual-line: #C8D8EA;
      --manual-muted: #64748B;
      --manual-soft: #F5F8FC;
      color: #1E293B;
      background: #FFFFFF;
      border: 1px solid var(--manual-line);
      border-radius: 8px;
      box-shadow: 0 18px 45px rgba(0, 0, 0, .18);
      line-height: 1.78;
      overflow: hidden;
    }}
    {scope} .manual-inner {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 42px 48px 64px;
      background: #FFFFFF;
    }}
    {scope} h1 {{
      margin: 0 0 10px;
      color: var(--manual-blue);
      font-size: 2.35rem;
      line-height: 1.2;
    }}
    {scope} h2 {{
      color: var(--manual-blue);
      font-size: 1.65rem;
      margin: 42px 0 16px;
      padding-bottom: 8px;
      border-bottom: 2px solid #E8F0FA;
    }}
    {scope} h3 {{
      color: #2E74B5;
      font-size: 1.15rem;
      margin: 22px 0 10px;
    }}
    {scope} p {{ margin: 8px 0; }}
    {scope} ol, {scope} ul {{ padding-left: 24px; }}
    {scope} li {{ margin: 7px 0; }}
    {scope} code {{
      color: #1F4D78;
      background: #EAF2FB;
      padding: 2px 6px;
      border-radius: 5px;
    }}
    {scope} .manual-eyebrow {{
      margin: 0 0 8px;
      color: #2E74B5;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0;
    }}
    {scope} .manual-lead {{ color: var(--manual-muted); font-size: 1.02rem; }}
    {scope} .manual-hero {{
      padding: 30px 32px;
      background: linear-gradient(180deg, #F8FBFF, #FFFFFF);
      border: 1px solid var(--manual-line);
      border-radius: 8px;
    }}
    {scope} .manual-note {{
      margin: 18px 0 0;
      padding: 16px 18px;
      border-radius: 8px;
      border: 1px solid #E6C75F;
      background: #FFF8E1;
      color: #4A3B00;
    }}
    {scope} .manual-note.success {{
      border-color: #B7E4C7;
      background: #EFFAF3;
      color: #0F5132;
    }}
    {scope} .manual-card {{
      border: 1px solid var(--manual-line);
      background: var(--manual-soft);
      border-radius: 8px;
      padding: 18px 20px;
      margin: 14px 0;
    }}
    {scope} .manual-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
      margin: 16px 0;
    }}
    {scope} .manual-step-title {{
      color: var(--manual-blue);
      font-weight: 700;
      margin-bottom: 6px;
    }}
    {scope} .shot {{
      margin: 22px 0 30px;
      border: 1px solid var(--manual-line);
      background: #FFFFFF;
      border-radius: 8px;
      overflow: hidden;
    }}
    {scope} .shot img {{
      display: block;
      width: 100%;
      height: auto;
      border-bottom: 1px solid var(--manual-line);
    }}
    {scope} .shot figcaption {{
      padding: 10px 16px;
      color: var(--manual-muted);
      background: #F8FBFF;
      font-size: .92rem;
    }}
    {scope} .manual-footer {{
      margin-top: 44px;
      padding-top: 18px;
      border-top: 1px solid var(--manual-line);
      color: var(--manual-muted);
      font-size: .92rem;
    }}
    @media (max-width: 900px) {{
      {scope} .manual-inner {{ padding: 24px 18px 42px; }}
      {scope} .manual-grid {{ grid-template-columns: 1fr; }}
      {scope} h1 {{ font-size: 1.8rem; }}
    }}
"""


def build_html():
    MANUAL_DIR.mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    make_workflow_image()
    make_update_image()
    make_install_image()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    body_content = manual_body(now)
    fragment = f"""<article class="manual-document">
  <div class="manual-inner">
{body_content}
  </div>
</article>
"""
    html = f"""<!doctype html>
<html lang="th">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>คู่มือการใช้งาน Data Exchange Tools</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", Tahoma, sans-serif;
      background: #EEF4FA;
      padding: 36px 18px;
    }}
    main {{
      width: min(1160px, 100%);
      margin: 0 auto;
    }}
    {manual_css(".manual-document")}
  </style>
</head>
<body>
  <main>
{fragment}
  </main>
</body>
</html>
"""
    OUT_HTML.write_text(html, encoding="utf-8")
    STATIC_MANUAL_HTML.write_text(html, encoding="utf-8")
    STATIC_MANUAL_FRAGMENT.write_text(fragment, encoding="utf-8")
    STATIC_IMG_DIR.mkdir(parents=True, exist_ok=True)
    for image_path in IMG_DIR.glob("*.png"):
        shutil.copy2(image_path, STATIC_IMG_DIR / image_path.name)
    print(f"created {OUT_HTML}")
    print(f"created {STATIC_MANUAL_HTML}")


if __name__ == "__main__":
    build_html()
