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
COMPANY_LOGO_PATH = "app/resources/images/jip_logo.png"


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


def _wrap_text_lines(c, text, max_width, font_name="Helvetica", font_size=9):
    words = str(text or "").split()
    lines = []
    line = ""

    for word in words:
        test_line = f"{line} {word}".strip()

        if c.stringWidth(test_line, font_name, font_size) <= max_width:
            line = test_line
        else:
            if line:
                lines.append(line)
            line = word

    if line:
        lines.append(line)

    return lines if lines else ["-"]


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


def _draw_bilingual_left(
    c,
    malay,
    english,
    x,
    y,
    malay_font="Helvetica-Bold",
    english_font="Helvetica-Oblique",
    malay_size=9,
    english_size=8,
    malay_color=colors.black,
    english_color=colors.HexColor("#666666"),
    line_gap=11,
):
    """
    Draw Malay in bold and English in italic below it.
    Returns the next Y position.
    """
    c.setFillColor(malay_color)
    c.setFont(malay_font, malay_size)
    c.drawString(x, y, str(malay))

    c.setFillColor(english_color)
    c.setFont(english_font, english_size)
    c.drawString(x, y - line_gap, str(english))

    return y - (line_gap + 3)


def _draw_bilingual_right(
    c,
    malay,
    english,
    x,
    y,
    malay_font="Helvetica-Bold",
    english_font="Helvetica-Oblique",
    malay_size=9,
    english_size=8,
    malay_color=colors.black,
    english_color=colors.HexColor("#666666"),
    line_gap=11,
):
    c.setFillColor(malay_color)
    c.setFont(malay_font, malay_size)
    c.drawRightString(x, y, str(malay))

    c.setFillColor(english_color)
    c.setFont(english_font, english_size)
    c.drawRightString(x, y - line_gap, str(english))

    return y - (line_gap + 3)


def _draw_bilingual_center(
    c,
    malay,
    english,
    x,
    y,
    malay_font="Helvetica-Bold",
    english_font="Helvetica-Oblique",
    malay_size=9,
    english_size=8,
    malay_color=colors.black,
    english_color=colors.HexColor("#666666"),
    line_gap=11,
):
    c.setFillColor(malay_color)
    c.setFont(malay_font, malay_size)
    c.drawCentredString(x, y, str(malay))

    c.setFillColor(english_color)
    c.setFont(english_font, english_size)
    c.drawCentredString(x, y - line_gap, str(english))

    return y - (line_gap + 3)


def _draw_bilingual_label_value(
    c,
    malay_label,
    english_label,
    value,
    x,
    y,
    max_width,
    label_width=125,
    malay_size=8.5,
    english_size=7.5,
    value_size=9,
    malay_color=colors.HexColor("#222222"),
    english_color=colors.HexColor("#666666"),
):
    """
    Draw a two-line label:
    Malay bold on top, English italic below.
    Value is drawn on the right side.
    """
    c.setFillColor(malay_color)
    c.setFont("Helvetica-Bold", malay_size)
    c.drawString(x, y, malay_label)

    c.setFillColor(english_color)
    c.setFont("Helvetica-Oblique", english_size)
    c.drawString(x, y - 10, english_label)

    c.setFillColor(colors.HexColor("#222222"))
    c.setFont("Helvetica", value_size)

    value_x = x + label_width
    value_width = max_width - label_width

    value_lines = _wrap_text_lines(
        c,
        value,
        value_width,
        "Helvetica",
        value_size,
    )

    value_y = y

    for line in value_lines:
        c.drawString(value_x, value_y, line)
        value_y -= 11

    used_height = max(22, len(value_lines) * 11)

    return y - used_height


def _draw_bilingual_wrapped_center(
    c,
    malay_text,
    english_text,
    center_x,
    y,
    max_width,
    malay_size=7,
    english_size=7,
    line_height=9,
):
    """
    Draw Malay bold first, then English italic below.
    """
    malay_lines = _wrap_text_lines(
        c,
        malay_text,
        max_width,
        "Helvetica-Bold",
        malay_size,
    )

    c.setFillColor(colors.HexColor("#666666"))
    c.setFont("Helvetica-Bold", malay_size)

    for line in malay_lines:
        c.drawCentredString(center_x, y, line)
        y -= line_height

    y -= 2

    english_lines = _wrap_text_lines(
        c,
        english_text,
        max_width,
        "Helvetica-Oblique",
        english_size,
    )

    c.setFont("Helvetica-Oblique", english_size)

    for line in english_lines:
        c.drawCentredString(center_x, y, line)
        y -= line_height

    return y


# =========================================================
# BILINGUAL LABELS
# MALAY BOLD / ENGLISH ITALIC
# =========================================================

L = {
    "title_ms": "MAJLIS PERBANDARAN BENTONG",
    "title_en": "BENTONG MUNICIPAL COUNCIL",

    "doc_title_ms": "RESIT CUKAI TAKSIRAN",
    "doc_title_en": "ASSESSMENT TAX RECEIPT",

    "generated_by_ms": "Dijana oleh TIP Bentong",
    "generated_by_en": "Generated by TIP Bentong",

    "receipt_ms": "Resit",
    "receipt_en": "Receipt",

    "paid_at_ms": "Dibayar pada",
    "paid_at_en": "Paid at",

    "payment_method_ms": "Kaedah Pembayaran",
    "payment_method_en": "Payment Method",

    "bank_trx_ms": "No. Transaksi Bank",
    "bank_trx_en": "Bank Transaction No.",

    "table_col_hash_ms": "Bil.",
    "table_col_hash_en": "No.",

    "table_col_item_ms": "Butiran",
    "table_col_item_en": "Item",

    "table_col_amount_ms": "Jumlah",
    "table_col_amount_en": "Amount",

    "row_title_ms": "Cukai Taksiran",
    "row_title_en": "Assessment Tax",

    "account_number_ms": "Nombor Akaun",
    "account_number_en": "Account Number",

    "owner_name_ms": "Nama Pemilik",
    "owner_name_en": "Owner Name",

    "property_address_ms": "Alamat Harta",
    "property_address_en": "Property Address",

    "total_ms": "Jumlah Keseluruhan",
    "total_en": "Total Amount",

    "reminder_ms": (
        "Sila maklum bahawa bagi pelanggan yang membuat pembayaran, "
        "kemas kini baki akaun akan diproses pada hari berikutnya."
    ),

    "reminder_en": (
        "Please be informed that for customers making payments, "
        "the account balance update will be processed on the following day."
    ),

    "footer_name_ms": "Majlis Perbandaran Bentong",
    "footer_name_en": "Bentong Municipal Council",

    "footer_address": (
        "Jalan Ketari, 28700 Bentong, Pahang Darul Makmur"
    ),

    "footer_contact_ms": (
        "Telefon: 04-5497555 | Aplikasi: TIP Bentong"
    ),

    "footer_contact_en": (
        "Telephone: 04-5497555 | Application: TIP Bentong"
    ),
}


# =========================================================
# PAGE HEADER
# =========================================================

def _draw_page_header(
    c,
    width,
    height,
    primary_blue,
    secondary_blue,
    light_blue,
):
    header_height = 155

    # Main top design
    c.setFillColor(primary_blue)
    c.rect(
        0,
        height - header_height,
        width,
        header_height,
        fill=True,
        stroke=False,
    )

    c.setFillColor(secondary_blue)
    c.rect(
        0,
        height - 38,
        width,
        38,
        fill=True,
        stroke=False,
    )

    c.setFillColor(light_blue)
    c.rect(
        0,
        height - 12,
        width,
        12,
        fill=True,
        stroke=False,
    )

    c.setFillColor(colors.HexColor("#002B6B"))
    c.rect(
        0,
        height - header_height,
        width,
        38,
        fill=True,
        stroke=False,
    )

    # Bentong logo top left
    if BENTONG_LOGO:
        _draw_image_keep_ratio(
            c,
            BENTONG_LOGO,
            35,
            height - 122,
            85,
            85,
        )

    # Company logo top right
    if COMPANY_LOGO:
        _draw_image_keep_ratio(
            c,
            COMPANY_LOGO,
            width - 120,
            height - 112,
            120,
            70,
        )

    # Header center title
    _draw_bilingual_center(
        c,
        L["title_ms"],
        L["title_en"],
        width / 2,
        height - 48,
        malay_size=15,
        english_size=9,
        malay_color=colors.white,
        english_color=colors.white,
        line_gap=15,
    )

    c.setFillColor(colors.white)
    c.setFont("Helvetica", 8)
    c.drawCentredString(
        width / 2,
        height - 79,
        L["footer_address"],
    )

    _draw_bilingual_center(
        c,
        L["doc_title_ms"],
        L["doc_title_en"],
        width / 2,
        height - 98,
        malay_size=10,
        english_size=8,
        malay_color=colors.white,
        english_color=colors.white,
        line_gap=12,
    )

    _draw_bilingual_center(
        c,
        L["generated_by_ms"],
        L["generated_by_en"],
        width / 2,
        height - 125,
        malay_size=8,
        english_size=7,
        malay_color=colors.white,
        english_color=colors.white,
        line_gap=10,
    )


# =========================================================
# TABLE HEADER
# =========================================================

def _draw_table_header(
    c,
    y,
    table_left,
    table_right,
    table_width,
    secondary_blue,
):
    header_height = 44

    c.setFillColor(secondary_blue)
    c.roundRect(
        table_left,
        y,
        table_width,
        header_height,
        12,
        fill=True,
        stroke=False,
    )

    _draw_bilingual_left(
        c,
        L["table_col_hash_ms"],
        L["table_col_hash_en"],
        table_left + 18,
        y + 26,
        malay_size=9,
        english_size=8,
        malay_color=colors.white,
        english_color=colors.white,
        line_gap=11,
    )

    _draw_bilingual_left(
        c,
        L["table_col_item_ms"],
        L["table_col_item_en"],
        table_left + 55,
        y + 26,
        malay_size=9,
        english_size=8,
        malay_color=colors.white,
        english_color=colors.white,
        line_gap=11,
    )

    _draw_bilingual_right(
        c,
        L["table_col_amount_ms"],
        L["table_col_amount_en"],
        table_right - 18,
        y + 26,
        malay_size=9,
        english_size=8,
        malay_color=colors.white,
        english_color=colors.white,
        line_gap=11,
    )


# =========================================================
# FOOTER
# =========================================================

def _draw_footer(
    c,
    width,
    primary_blue,
    grey_text,
):
    c.setStrokeColor(colors.HexColor("#D9E8FF"))
    c.line(45, 88, width - 45, 88)

    if BENTONG_LOGO:
        _draw_image_keep_ratio(
            c,
            BENTONG_LOGO,
            50,
            25,
            35,
            35,
        )

    if COMPANY_LOGO:
        _draw_image_keep_ratio(
            c,
            COMPANY_LOGO,
            width - 100,
            25,
            55,
            35,
        )

    _draw_bilingual_center(
        c,
        L["footer_name_ms"],
        L["footer_name_en"],
        width / 2,
        69,
        malay_size=8,
        english_size=7,
        malay_color=primary_blue,
        english_color=grey_text,
        line_gap=10,
    )

    c.setFillColor(grey_text)
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(
        width / 2,
        45,
        L["footer_address"],
    )

    _draw_bilingual_center(
        c,
        L["footer_contact_ms"],
        L["footer_contact_en"],
        width / 2,
        33,
        malay_size=7,
        english_size=6.5,
        malay_color=grey_text,
        english_color=grey_text,
        line_gap=9,
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

    table_left = 45
    table_right = width - 45
    table_width = table_right - table_left

    footer_safe_y = 125
    item_gap = 10
    total_gap = 24

    _draw_page_header(
        c,
        width,
        height,
        primary_blue,
        secondary_blue,
        light_blue,
    )

    # =====================================================
    # RECEIPT TITLE AND PAYMENT INFORMATION
    # =====================================================

    y = height - 202

    _draw_bilingual_left(
        c,
        L["receipt_ms"],
        L["receipt_en"],
        45,
        y,
        malay_size=22,
        english_size=12,
        malay_color=primary_blue,
        english_color=secondary_blue,
        line_gap=17,
    )

    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(secondary_blue)
    c.drawString(
        45,
        y - 38,
        f"#{order_no or '-'}",
    )

    metadata_y = y - 62

    metadata_y = _draw_bilingual_label_value(
        c,
        L["paid_at_ms"],
        L["paid_at_en"],
        paid_date.strftime("%d %b %Y"),
        45,
        metadata_y,
        max_width=420,
        label_width=135,
        malay_size=8.5,
        english_size=7.5,
        value_size=9,
    )

    metadata_y -= 3

    metadata_y = _draw_bilingual_label_value(
        c,
        L["payment_method_ms"],
        L["payment_method_en"],
        payment_method or "-",
        45,
        metadata_y,
        max_width=420,
        label_width=135,
        malay_size=8.5,
        english_size=7.5,
        value_size=9,
    )

    if bank_trx_no:
        metadata_y -= 3

        _draw_bilingual_label_value(
            c,
            L["bank_trx_ms"],
            L["bank_trx_en"],
            bank_trx_no,
            45,
            metadata_y,
            max_width=470,
            label_width=135,
            malay_size=8.5,
            english_size=7.5,
            value_size=9,
        )

    # =====================================================
    # TABLE HEADER
    # =====================================================

    y = height - 355

    _draw_table_header(
        c,
        y,
        table_left,
        table_right,
        table_width,
        secondary_blue,
    )

    y -= 50

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

        address_lines = _wrap_text_lines(
            c,
            property_address,
            max_width=260,
            font_name="Helvetica",
            font_size=9,
        )

        row_height = max(
            145,
            126 + (len(address_lines) * 11),
        )

        # Page break before drawing item
        if y - row_height < footer_safe_y:
            _draw_footer(
                c,
                width,
                primary_blue,
                grey_text,
            )

            c.showPage()

            _draw_page_header(
                c,
                width,
                height,
                primary_blue,
                secondary_blue,
                light_blue,
            )

            y = height - 220

            _draw_table_header(
                c,
                y,
                table_left,
                table_right,
                table_width,
                secondary_blue,
            )

            y -= 50

        # Item background
        c.setFillColor(
            soft_blue if index % 2 == 0 else colors.white
        )

        c.roundRect(
            table_left,
            y - row_height,
            table_width,
            row_height,
            9,
            fill=True,
            stroke=False,
        )

        # Border
        c.setStrokeColor(
            colors.HexColor("#D9E8FF")
        )

        c.roundRect(
            table_left,
            y - row_height,
            table_width,
            row_height,
            9,
            fill=False,
            stroke=True,
        )

        # Item number
        c.setFillColor(dark_text)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(
            table_left + 18,
            y - 23,
            str(index),
        )

        # Item title Malay bold / English italic
        _draw_bilingual_left(
            c,
            L["row_title_ms"],
            L["row_title_en"],
            table_left + 55,
            y - 20,
            malay_size=11,
            english_size=8.5,
            malay_color=primary_blue,
            english_color=grey_text,
            line_gap=12,
        )

        # Amount
        c.setFillColor(primary_blue)
        c.setFont("Helvetica-Bold", 10)

        c.drawRightString(
            table_right - 18,
            y - 22,
            f"RM {_format_money(amount)}",
        )

        info_y = y - 54
        content_width = 330

        info_y = _draw_bilingual_label_value(
            c,
            L["account_number_ms"],
            L["account_number_en"],
            account_number,
            table_left + 55,
            info_y,
            max_width=content_width,
            label_width=110,
            malay_size=8,
            english_size=7,
            value_size=8.5,
        )

        info_y -= 3

        info_y = _draw_bilingual_label_value(
            c,
            L["owner_name_ms"],
            L["owner_name_en"],
            owner_name,
            table_left + 55,
            info_y,
            max_width=content_width,
            label_width=110,
            malay_size=8,
            english_size=7,
            value_size=8.5,
        )

        info_y -= 3

        c.setFillColor(dark_text)
        c.setFont("Helvetica-Bold", 8)

        c.drawString(
            table_left + 55,
            info_y,
            L["property_address_ms"],
        )

        c.setFillColor(grey_text)
        c.setFont("Helvetica-Oblique", 7)

        c.drawString(
            table_left + 55,
            info_y - 10,
            L["property_address_en"],
        )

        info_y -= 24

        c.setFillColor(colors.HexColor("#333333"))
        c.setFont("Helvetica", 8.5)

        for line in address_lines:
            c.drawString(
                table_left + 55,
                info_y,
                line,
            )
            info_y -= 11

        y -= row_height + item_gap

    # =====================================================
    # TOTAL BAR
    # =====================================================

    y -= total_gap

    total_bar_height = 50
    reminder_space = 75

    if (
        y
        - total_bar_height
        - reminder_space
        < footer_safe_y
    ):
        _draw_footer(
            c,
            width,
            primary_blue,
            grey_text,
        )

        c.showPage()

        _draw_page_header(
            c,
            width,
            height,
            primary_blue,
            secondary_blue,
            light_blue,
        )

        y = height - 220

    c.setFillColor(primary_blue)

    c.roundRect(
        table_left,
        y - total_bar_height,
        table_width,
        total_bar_height,
        12,
        fill=True,
        stroke=False,
    )

    _draw_bilingual_left(
        c,
        L["total_ms"],
        L["total_en"],
        table_left + 18,
        y - 20,
        malay_size=12,
        english_size=8,
        malay_color=colors.white,
        english_color=colors.white,
        line_gap=12,
    )

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 13)

    c.drawRightString(
        table_right - 18,
        y - 29,
        f"RM {_format_money(total_amount)}",
    )

    y -= total_bar_height + 30

    # =====================================================
    # REMINDER
    # =====================================================

    y = _draw_bilingual_wrapped_center(
        c,
        L["reminder_ms"],
        L["reminder_en"],
        width / 2,
        y,
        table_width - 40,
        malay_size=7,
        english_size=7,
        line_height=9,
    )

    # =====================================================
    # FOOTER
    # =====================================================

    _draw_footer(
        c,
        width,
        primary_blue,
        grey_text,
    )

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
                "property_address": (
                    "64, TAMAN PERDANA RAYA, "
                    "28600 KARAK"
                ),
                "amount": 273.60,
            },
            {
                "account_number": "T0602002856402",
                "owner_name": "ALI BIN ABU",
                "property_address": (
                    "NO 12, TAMAN BENTONG, "
                    "28700 BENTONG"
                ),
                "amount": 150.00,
            },
            {
                "account_number": "T0602002856403",
                "owner_name": "TEST OWNER",
                "property_address": (
                    "NO 99, JALAN CONTOH YANG PANJANG, "
                    "TAMAN CONTOH, 28700 BENTONG, "
                    "PAHANG DARUL MAKMUR"
                ),
                "amount": 88.90,
            },
        ],
    )

    with open(
        "tax_receipt_bentong.pdf",
        "wb",
    ) as output_file:
        output_file.write(pdf_bytes)

    print(
        "PDF generated: "
        "tax_receipt_bentong.pdf"
    )