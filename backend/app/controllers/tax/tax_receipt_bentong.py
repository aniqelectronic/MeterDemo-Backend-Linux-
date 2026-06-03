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

MAIN_LOGO = None
MAIN_LOGO_PATH = "app/resources/images/City_Car_Park_logo.png"

try:
    if os.path.exists(MAIN_LOGO_PATH):
        with open(MAIN_LOGO_PATH, "rb") as f:
            MAIN_LOGO = ImageReader(BytesIO(f.read()))
        print("[INFO] Main logo preloaded successfully.")
    else:
        print(f"[WARN] Main logo not found at: {MAIN_LOGO_PATH}")
except Exception as e:
    print(f"[WARN] Failed to load main logo: {e}")


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
    """
    Generate PBT Bentong Assessment Tax receipt PDF bytes.

    tax_items example:
    [
        {
            "account_number": "T0602002856401",
            "owner_name": "ZALINA BINTI MD AKHIR",
            "property_address": "64, TAMAN PERDANA RAYA, 28600 KARAK",
            "amount": 273.60
        },
        {
            "account_number": "T0602002856402",
            "owner_name": "ALI BIN ABU",
            "property_address": "NO 12, TAMAN BENTONG, 28700 BENTONG",
            "amount": 150.00
        }
    ]
    """

    if tax_items is None:
        tax_items = []

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    dark_blue = colors.HexColor("#083B73")
    light_blue = colors.HexColor("#12A8E0")
    green = colors.HexColor("#6DBB2F")
    grey_text = colors.HexColor("#666666")
    dark_text = colors.HexColor("#222222")

    # =====================================================
    # HEADER BACKGROUND
    # =====================================================

    header_height = 145

    c.setFillColor(light_blue)
    c.rect(0, height - header_height, width, header_height, fill=True, stroke=False)

    c.setFillColor(green)
    c.roundRect(
        width * 0.35,
        height - header_height - 10,
        width * 0.75,
        65,
        35,
        fill=True,
        stroke=False,
    )

    # =====================================================
    # LOGO
    # =====================================================

    if MAIN_LOGO:
        try:
            img_width, img_height = MAIN_LOGO.getSize()
            display_width = 80
            display_height = display_width * img_height / img_width

            c.drawImage(
                MAIN_LOGO,
                45,
                height - 105,
                width=display_width,
                height=display_height,
                mask="auto",
            )
        except Exception as e:
            print(f"[WARN] Failed to draw logo: {e}")

    # =====================================================
    # COUNCIL INFO
    # =====================================================

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(145, height - 50, "Majlis Perbandaran Bentong")

    c.setFont("Helvetica", 8)
    c.drawString(145, height - 65, "Jalan Ketari")
    c.drawString(145, height - 78, "28700 Bentong")
    c.drawString(145, height - 91, "Pahang Darul Makmur")
    c.drawString(145, height - 112, "Telephone : 04-5497555")
    c.drawString(145, height - 125, "Application : TIP Bentong")

    # =====================================================
    # TITLE
    # =====================================================

    y = height - 195

    c.setFillColor(dark_text)
    c.setFont("Helvetica-Bold", 26)
    c.drawString(45, y, "Receipt")

    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(grey_text)
    c.drawString(150, y + 4, f"#{order_no}")

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

    c.setFillColor(dark_blue)
    c.roundRect(table_left, y, table_width, 34, 15, fill=True, stroke=False)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(table_left + 18, y + 11, "#")
    c.drawString(table_left + 55, y + 11, "Item")
    c.drawRightString(table_right - 18, y + 11, "Amount")

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
            c.showPage()
            y = height - 80

            c.setFillColor(dark_blue)
            c.roundRect(table_left, y, table_width, 34, 15, fill=True, stroke=False)

            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(table_left + 18, y + 11, "#")
            c.drawString(table_left + 55, y + 11, "Item")
            c.drawRightString(table_right - 18, y + 11, "Amount")

            y -= 32

        c.setFillColor(colors.white)
        c.rect(table_left, y - 95, table_width, 95, fill=True, stroke=False)

        c.setFillColor(dark_text)
        c.setFont("Helvetica", 10)
        c.drawString(table_left + 18, y - 20, str(index))

        c.setFont("Helvetica-Bold", 11)
        c.drawString(table_left + 55, y - 20, "Assessment Tax")

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

        c.setFillColor(dark_text)
        c.setFont("Helvetica", 10)
        c.drawRightString(table_right - 18, y - 20, f"RM {_format_money(amount)}")

        y -= 105

    # =====================================================
    # TOTAL BAR
    # =====================================================

    if y < 120:
        c.showPage()
        y = height - 80

    c.setFillColor(dark_blue)
    c.roundRect(table_left, y - 10, table_width, 34, 15, fill=True, stroke=False)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(table_right - 18, y + 1, f"RM {_format_money(total_amount)}")

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

    c.setStrokeColor(colors.HexColor("#DDDDDD"))
    c.line(45, 80, width - 45, 80)

    c.setFillColor(grey_text)
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, 60, "Majlis Perbandaran Bentong")
    c.drawCentredString(width / 2, 47, "Jalan Ketari, 28700 Bentong, Pahang Darul Makmur")
    c.drawCentredString(width / 2, 34, "Telephone : 04-5497555 | Application : Vista Smart Kiosk")

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
        receipt_no="01B4P3VDXW",
        paid_date=datetime.datetime.now(),
        payment_method="FPX",
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