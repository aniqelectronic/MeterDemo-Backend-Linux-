from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from io import BytesIO
import datetime
import os


# =========================================================
# LOGO PRELOAD
# =========================================================

BENTONG_LOGO = None
BENTONG_LOGO_PATH = "app/resources/images/majlisbentong.png"

COMPANY_LOGO = None
COMPANY_LOGO_PATH = "app/resources/images/City_Car_Park_logo.png"


try:
    if os.path.exists(BENTONG_LOGO_PATH):
        with open(BENTONG_LOGO_PATH, "rb") as f:
            BENTONG_LOGO = ImageReader(BytesIO(f.read()))
        print("[INFO] Bentong logo preloaded successfully.")
    else:
        print(f"[WARN] Bentong logo not found at: {BENTONG_LOGO_PATH}")
except Exception as e:
    print(f"[WARN] Failed to load Bentong logo: {e}")


try:
    if os.path.exists(COMPANY_LOGO_PATH):
        with open(COMPANY_LOGO_PATH, "rb") as f:
            COMPANY_LOGO = ImageReader(BytesIO(f.read()))
        print("[INFO] Company logo preloaded successfully.")
    else:
        print(f"[WARN] Company logo not found at: {COMPANY_LOGO_PATH}")
except Exception as e:
    print(f"[WARN] Failed to load company logo: {e}")


# =========================================================
# HELPERS
# =========================================================

def _format_money(value):
    try:
        return f"{float(value):,.2f}"
    except Exception:
        return "0.00"


def _draw_wrapped_text(
    c,
    text,
    x,
    y,
    max_width,
    font_name="Helvetica",
    font_size=9,
    line_height=11,
):
    c.setFont(font_name, font_size)

    words = str(text or "").split()
    line = ""

    for word in words:
        test_line = f"{line} {word}".strip()

        if c.stringWidth(test_line, font_name, font_size) <= max_width:
            line = test_line
        else:
            c.drawString(x, y, line)
            y -= line_height
            line = word

    if line:
        c.drawString(x, y, line)
        y -= line_height

    return y


def _draw_image_keep_ratio(c, img, x, y, max_width, max_height):
    try:
        img_width, img_height = img.getSize()
        ratio = min(max_width / img_width, max_height / img_height)
        draw_width = img_width * ratio
        draw_height = img_height * ratio

        c.drawImage(
            img,
            x,
            y + (max_height - draw_height) / 2,
            width=draw_width,
            height=draw_height,
            mask="auto",
        )
    except Exception as e:
        print(f"[WARN] Failed to draw image: {e}")


def _draw_page_header(c, width, height, primary_blue, secondary_blue, light_blue):
    header_height = 150

    # Main blue header
    c.setFillColor(primary_blue)
    c.rect(0, height - header_height, width, header_height, fill=True, stroke=False)

    # Light blue strip
    c.setFillColor(light_blue)
    c.rect(0, height - 15, width, 15, fill=True, stroke=False)

    # Bottom blue strip
    c.setFillColor(secondary_blue)
    c.rect(0, height - header_height, width, 45, fill=True, stroke=False)

    # Bentong logo top left
    if BENTONG_LOGO:
        _draw_image_keep_ratio(
            c,
            BENTONG_LOGO,
            35,
            height - 115,
            80,
            80,
        )

    # Company logo top right
    if COMPANY_LOGO:
        _draw_image_keep_ratio(
            c,
            COMPANY_LOGO,
            width - 150,
            height - 108,
            110,
            65,
        )

    # Center text
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(width / 2, height - 50, "MAJLIS PERBANDARAN BENTONG")

    c.setFont("Helvetica", 9)
    c.drawCentredString(
        width / 2,
        height - 67,
        "Jalan Ketari, 28700 Bentong, Pahang Darul Makmur",
    )
    c.drawCentredString(width / 2, height - 82, "Assessment Tax Receipt")
    c.drawCentredString(width / 2, height - 97, "Powered by Vista Smart Kiosk")


def _draw_table_header(c, y, table_left, table_right, table_width, secondary_blue):
    c.setFillColor(secondary_blue)
    c.roundRect(table_left, y, table_width, 34, 12, fill=True, stroke=False)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(table_left + 18, y + 11, "#")
    c.drawString(table_left + 55, y + 11, "Item")
    c.drawRightString(table_right - 18, y + 11, "Amount")


def _draw_footer(c, width, primary_blue, grey_text):
    c.setStrokeColor(colors.HexColor("#D9E8FF"))
    c.line(45, 82, width - 45, 82)

    if BENTONG_LOGO:
        _draw_image_keep_ratio(c, BENTONG_LOGO, 50, 25, 35, 35)

    if COMPANY_LOGO:
        _draw_image_keep_ratio(c, COMPANY_LOGO, width - 95, 25, 50, 35)

    c.setFillColor(primary_blue)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(width / 2, 62, "Majlis Perbandaran Bentong")

    c.setFillColor(grey_text)
    c.setFont("Helvetica", 8)
    c.drawCentredString(
        width / 2,
        48,
        "Jalan Ketari, 28700 Bentong, Pahang Darul Makmur",
    )
    c.drawCentredString(
        width / 2,
        34,
        "Telephone : 04-5497555 | Application : TIP BENTONG",
    )


# =========================================================
# TAX RECEIPT GENERATOR - PBT BENTONG
# =========================================================

def generate_tax_receipt_bentong(
    paid_date: datetime.datetime,
    payment_method: str,
    tax_items: list = None,
    order_no: str = None,
    bank_trx_no: str = None,
):
    if tax_items is None:
        tax_items = []

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    primary_blue = colors.HexColor("#003B8E")
    secondary_blue = colors.HexColor("#0057D9")
    light_blue = colors.HexColor("#0A84FF")
    soft_blue = colors.HexColor("#EDF4FF")
    grey_text = colors.HexColor("#666666")
    dark_text = colors.HexColor("#222222")

    _draw_page_header(c, width, height, primary_blue, secondary_blue, light_blue)

    # =====================================================
    # TITLE
    # =====================================================

    y = height - 195

    c.setFillColor(primary_blue)
    c.setFont("Helvetica-Bold", 26)
    c.drawString(45, y, "Receipt")

    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(secondary_blue)
    c.drawString(150, y + 4, f"#{order_no or '-'}")

    c.setFont("Helvetica", 10)
    c.setFillColor(grey_text)
    c.drawString(45, y - 22, f"Paid at {paid_date.strftime('%d %b %Y')}")
    c.drawString(45, y - 38, f"Payment Method: {payment_method}")

    extra_y = y - 54

    if bank_trx_no:
        c.drawString(45, extra_y, f"Bank Transaction No: {bank_trx_no}")
        extra_y -= 16

    # =====================================================
    # TABLE HEADER
    # =====================================================

    table_left = 45
    table_right = width - 45
    table_width = table_right - table_left

    y -= 105

    _draw_table_header(c, y, table_left, table_right, table_width, secondary_blue)

    y -= 32

    # =====================================================
    # TAX ITEMS
    # =====================================================

    total_amount = 0.0

    for index, item in enumerate(tax_items, start=1):
        account_number = item.get("account_number", "-")
        owner_name = item.get("owner_name", "-")
        property_address = item.get("property_address", "-")
        amount = float(item.get("amount", 0) or 0)

        total_amount += amount

        if y < 165:
            _draw_footer(c, width, primary_blue, grey_text)
            c.showPage()

            _draw_page_header(c, width, height, primary_blue, secondary_blue, light_blue)

            y = height - 190
            _draw_table_header(c, y, table_left, table_right, table_width, secondary_blue)
            y -= 32

        # Item background
        c.setFillColor(soft_blue if index % 2 == 0 else colors.white)
        c.roundRect(
            table_left,
            y - 95,
            table_width,
            95,
            8,
            fill=True,
            stroke=False,
        )

        c.setFillColor(dark_text)
        c.setFont("Helvetica", 10)
        c.drawString(table_left + 18, y - 20, str(index))

        c.setFillColor(primary_blue)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(table_left + 55, y - 20, "Assessment Tax")

        c.setFillColor(dark_text)
        c.setFont("Helvetica", 9)

        info_y = y - 38
        c.drawString(table_left + 55, info_y, f"Account Number: {account_number}")

        info_y -= 13
        c.drawString(table_left + 55, info_y, f"Owner Name: {owner_name}")

        info_y -= 13
        c.drawString(table_left + 55, info_y, "Property Address:")

        info_y -= 12
        c.setFillColor(colors.HexColor("#333333"))

        _draw_wrapped_text(
            c,
            property_address,
            table_left + 55,
            info_y,
            max_width=300,
            font_name="Helvetica",
            font_size=9,
            line_height=11,
        )

        c.setFillColor(primary_blue)
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(table_right - 18, y - 20, f"RM {_format_money(amount)}")

        y -= 105

    # =====================================================
    # TOTAL BAR
    # =====================================================

    if y < 120:
        _draw_footer(c, width, primary_blue, grey_text)
        c.showPage()

        _draw_page_header(c, width, height, primary_blue, secondary_blue, light_blue)
        y = height - 190

    c.setFillColor(primary_blue)
    c.roundRect(table_left, y - 10, table_width, 36, 12, fill=True, stroke=False)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(table_left + 18, y + 2, "Total")

    c.drawRightString(table_right - 18, y + 2, f"RM {_format_money(total_amount)}")

    y -= 60

    # =====================================================
    # REMINDER
    # =====================================================

    c.setFillColor(grey_text)
    c.setFont("Helvetica", 7)
    c.drawCentredString(
        width / 2,
        y,
        "Please be informed that for customers making payments, the updating of account balances will be processed on the following day.",
    )

    # =====================================================
    # FOOTER
    # =====================================================

    _draw_footer(c, width, primary_blue, grey_text)

    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer.read()


# =========================================================
# TEST SAVE PDF
# Remove this part when using inside FastAPI endpoint
# =========================================================

if __name__ == "__main__":
    pdf_bytes = generate_tax_receipt_bentong(
        paid_date=datetime.datetime.now(),
        payment_method="DuitNow QR",
        order_no="ORD123456",
        bank_trx_no="BANK987654",
        tax_items=[
            {
                "account_number": "T0602002856401",
                "owner_name": "ZALINA BINTI MD AKHIR",
                "property_address": "64, TAMAN PERDANA RAYA, 28600 KARAK",
                "amount": 273.60,
            },
            {
                "account_number": "T0602002856402",
                "owner_name": "ALI BIN ABU",
                "property_address": "NO 12, TAMAN BENTONG, 28700 BENTONG",
                "amount": 150.00,
            },
        ],
    )

    with open("tax_receipt_bentong.pdf", "wb") as f:
        f.write(pdf_bytes)

    print("PDF generated: tax_receipt_bentong.pdf")