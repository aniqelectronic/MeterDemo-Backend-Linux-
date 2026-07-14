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
        print(
            f"[WARN] Bentong logo not found at: "
            f"{BENTONG_LOGO_PATH}"
        )

except Exception as e:
    print(f"[WARN] Failed to load Bentong logo: {e}")


try:
    if os.path.exists(COMPANY_LOGO_PATH):
        with open(COMPANY_LOGO_PATH, "rb") as f:
            COMPANY_LOGO = ImageReader(BytesIO(f.read()))

        print("[INFO] Company logo preloaded successfully.")
    else:
        print(
            f"[WARN] Company logo not found at: "
            f"{COMPANY_LOGO_PATH}"
        )

except Exception as e:
    print(f"[WARN] Failed to load company logo: {e}")


# =========================================================
# HELPERS
# =========================================================

def _format_money(value):
    try:
        return f"{float(value or 0):,.2f}"
    except (TypeError, ValueError):
        return "0.00"


def _safe_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _safe_text(value):
    value = str(value or "").strip()
    return value if value else "-"


def _format_date(value):
    if not value:
        return "-"

    try:
        if isinstance(value, datetime.datetime):
            return value.strftime("%d %b %Y")

        if isinstance(value, datetime.date):
            return value.strftime("%d %b %Y")

        parsed_date = datetime.datetime.strptime(
            str(value),
            "%Y-%m-%d",
        )

        return parsed_date.strftime("%d %b %Y")

    except Exception:
        return str(value)


def _build_address(*parts):
    cleaned = []

    for part in parts:
        part = str(part or "").strip()

        if part:
            cleaned.append(part)

    return ", ".join(cleaned) if cleaned else "-"


def _wrap_text_lines(
    c,
    text,
    max_width,
    font_name="Helvetica",
    font_size=9,
):
    words = str(text or "-").split()
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()

        if (
            c.stringWidth(
                test_line,
                font_name,
                font_size,
            )
            <= max_width
        ):
            current_line = test_line

        else:
            if current_line:
                lines.append(current_line)

            current_line = word

    if current_line:
        lines.append(current_line)

    return lines if lines else ["-"]


def _draw_image_keep_ratio(
    c,
    img,
    x,
    y,
    max_width,
    max_height,
):
    try:
        image_width, image_height = img.getSize()

        ratio = min(
            max_width / image_width,
            max_height / image_height,
        )

        draw_width = image_width * ratio
        draw_height = image_height * ratio

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
    malay_size=9,
    english_size=8,
    malay_color=colors.black,
    english_color=colors.HexColor("#666666"),
    line_gap=11,
):
    c.setFillColor(malay_color)
    c.setFont("Helvetica-Bold", malay_size)
    c.drawString(x, y, str(malay))

    c.setFillColor(english_color)
    c.setFont("Helvetica-Oblique", english_size)
    c.drawString(x, y - line_gap, str(english))

    return y - line_gap - 3


def _draw_bilingual_right(
    c,
    malay,
    english,
    x,
    y,
    malay_size=9,
    english_size=8,
    malay_color=colors.black,
    english_color=colors.HexColor("#666666"),
    line_gap=11,
):
    c.setFillColor(malay_color)
    c.setFont("Helvetica-Bold", malay_size)
    c.drawRightString(x, y, str(malay))

    c.setFillColor(english_color)
    c.setFont("Helvetica-Oblique", english_size)
    c.drawRightString(x, y - line_gap, str(english))

    return y - line_gap - 3


def _draw_bilingual_center(
    c,
    malay,
    english,
    x,
    y,
    malay_size=9,
    english_size=8,
    malay_color=colors.black,
    english_color=colors.HexColor("#666666"),
    line_gap=11,
):
    c.setFillColor(malay_color)
    c.setFont("Helvetica-Bold", malay_size)
    c.drawCentredString(x, y, str(malay))

    c.setFillColor(english_color)
    c.setFont("Helvetica-Oblique", english_size)
    c.drawCentredString(x, y - line_gap, str(english))

    return y - line_gap - 3


def _draw_bilingual_label_value(
    c,
    malay_label,
    english_label,
    value,
    x,
    y,
    max_width,
    label_width=135,
    malay_size=8.5,
    english_size=7.5,
    value_size=8.5,
    malay_color=colors.HexColor("#222222"),
    english_color=colors.HexColor("#666666"),
):
    c.setFillColor(malay_color)
    c.setFont("Helvetica-Bold", malay_size)
    c.drawString(x, y, str(malay_label))

    c.setFillColor(english_color)
    c.setFont("Helvetica-Oblique", english_size)
    c.drawString(x, y - 10, str(english_label))

    value_x = x + label_width
    value_width = max_width - label_width

    value_lines = _wrap_text_lines(
        c,
        value,
        value_width,
        "Helvetica",
        value_size,
    )

    c.setFillColor(colors.HexColor("#222222"))
    c.setFont("Helvetica", value_size)

    value_y = y

    for line in value_lines:
        c.drawString(
            value_x,
            value_y,
            line,
        )
        value_y -= 11

    used_height = max(
        22,
        len(value_lines) * 11,
    )

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
        c.drawCentredString(
            center_x,
            y,
            line,
        )
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
        c.drawCentredString(
            center_x,
            y,
            line,
        )
        y -= line_height

    return y


# =========================================================
# BILINGUAL LABELS
# MALAY BOLD / ENGLISH ITALIC
# =========================================================

L = {
    "title_ms": "MAJLIS PERBANDARAN BENTONG",
    "title_en": "BENTONG MUNICIPAL COUNCIL",

    "doc_title_ms": "RESIT BAYARAN SEWAAN",
    "doc_title_en": "RENTAL PAYMENT RECEIPT",

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

    "table_col_detail_ms": "Butiran Sewaan",
    "table_col_detail_en": "Rental Details",

    "table_col_amount_ms": "Jumlah Dibayar",
    "table_col_amount_en": "Amount Paid",

    "row_title_ms": "Sewaan",
    "row_title_en": "Rental",

    "account_number_ms": "Nombor Akaun",
    "account_number_en": "Account Number",

    "old_account_number_ms": "Nombor Akaun Lama",
    "old_account_number_en": "Old Account Number",

    "tenant_name_ms": "Nama Penyewa",
    "tenant_name_en": "Tenant Name",

    "registration_no_ms": "No. Pendaftaran",
    "registration_no_en": "Registration No.",

    "rental_period_ms": "Tempoh Sewaan",
    "rental_period_en": "Rental Period",

    "premise_address_ms": "Alamat Premis",
    "premise_address_en": "Premise Address",

    "mailing_address_ms": "Alamat Surat-Menyurat",
    "mailing_address_en": "Mailing Address",

    "outstanding_rent_ms": "Tunggakan Sewa",
    "outstanding_rent_en": "Outstanding Rent",

    "current_rent_ms": "Sewa Semasa",
    "current_rent_en": "Current Rental Fee",

    "water_charge_ms": "Caj Air",
    "water_charge_en": "Water Charge",

    "electric_charge_ms": "Caj Elektrik",
    "electric_charge_en": "Electric Charge",

    "management_charge_ms": "Caj Pengurusan",
    "management_charge_en": "Management Charge",

    "total_paid_ms": "Jumlah Dibayar",
    "total_paid_en": "Total Paid",

    "reminder_ms": (
        "Sila maklum bahawa kemas kini baki akaun mungkin "
        "diproses pada hari bekerja berikutnya."
    ),

    "reminder_en": (
        "Please be informed that account balance updates "
        "may be processed on the following working day."
    ),

    "footer_name_ms": "Majlis Perbandaran Bentong",
    "footer_name_en": "Bentong Municipal Council",

    "footer_address": (
        "Jalan Ketari, 28700 Bentong, "
        "Pahang Darul Makmur"
    ),

    "footer_contact_ms": (
        "Telefon: 04-5497555 | "
        "Aplikasi: TIP Bentong"
    ),

    "footer_contact_en": (
        "Telephone: 04-5497555 | "
        "Application: TIP Bentong"
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

    if BENTONG_LOGO:
        _draw_image_keep_ratio(
            c,
            BENTONG_LOGO,
            35,
            height - 122,
            85,
            85,
        )

    if COMPANY_LOGO:
        _draw_image_keep_ratio(
            c,
            COMPANY_LOGO,
            width - 120,
            height - 112,
            120,
            70,
        )

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
# FOOTER
# =========================================================

def _draw_footer(
    c,
    width,
    primary_blue,
    grey_text,
):
    c.setStrokeColor(
        colors.HexColor("#D9E8FF")
    )

    c.line(
        45,
        88,
        width - 45,
        88,
    )

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
        L["table_col_detail_ms"],
        L["table_col_detail_en"],
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
# NORMALIZE API DATA
# =========================================================

def build_sewaan_receipt_item_from_api(data):
    return {
        "account_number": data.get(
            "account_no",
            "-",
        ),

        "old_account_number": data.get(
            "old_account_no",
            "-",
        ),

        "tenant_name": data.get(
            "name",
            "-",
        ),

        "registration_no": data.get(
            "rent_pdaftaran",
            "-",
        ),

        "start_date": data.get(
            "start_date",
            "-",
        ),

        "end_date": data.get(
            "end_date",
            "-",
        ),

        "premise_address": _build_address(
            data.get("rent_alamatswn"),
            data.get("rent_jalanname"),
            data.get("rent_postcode"),
            data.get("rent_bandarnam"),
            data.get("rent_negeri"),
        ),

        "mailing_address": _build_address(
            data.get("alamat1"),
            data.get("alamat2"),
            data.get("alamat3"),
            data.get("alamat4"),
            data.get("postcode"),
            data.get("pekan_name"),
            data.get("ten_negeri"),
        ),

        "outstanding_rent": data.get(
            "tunggakan_sewa",
            "0",
        ),

        "current_rent": data.get(
            "rental_fee",
            data.get("sewa_semasa", "0"),
        ),

        "water_charge": data.get(
            "tunggakan_caj_air",
            "0",
        ),

        "electric_charge": data.get(
            "tunggakan_caj_elektrik",
            "0",
        ),

        "management_charge": data.get(
            "tunggakan_caj_pengurusan",
            "0",
        ),

        "amount": data.get(
            "jumlah",
            "0",
        ),
    }


# =========================================================
# SEWAAN RECEIPT GENERATOR - PBT BENTONG
# =========================================================

def generate_sewaan_receipt_bentong(
    paid_date: datetime.datetime,
    payment_method: str,
    sewaan_items: list = None,
    order_no: str = None,
    bank_trx_no: str = None,
):
    if sewaan_items is None:
        sewaan_items = []

    buffer = BytesIO()

    c = canvas.Canvas(
        buffer,
        pagesize=A4,
    )

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
        paid_date.strftime(
            "%d %b %Y %I:%M %p"
        ),
        45,
        metadata_y,
        max_width=470,
        label_width=145,
        malay_size=8.5,
        english_size=7.5,
        value_size=9,
    )

    metadata_y -= 3

    metadata_y = _draw_bilingual_label_value(
        c,
        L["payment_method_ms"],
        L["payment_method_en"],
        _safe_text(payment_method),
        45,
        metadata_y,
        max_width=470,
        label_width=145,
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
            _safe_text(bank_trx_no),
            45,
            metadata_y,
            max_width=470,
            label_width=145,
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

    total_amount = 0.0

    # =====================================================
    # RENTAL ITEMS
    # =====================================================

    for index, item in enumerate(
        sewaan_items,
        start=1,
    ):
        account_number = _safe_text(
            item.get("account_number")
        )

        old_account_number = _safe_text(
            item.get("old_account_number")
        )

        tenant_name = _safe_text(
            item.get("tenant_name")
        )

        registration_no = _safe_text(
            item.get("registration_no")
        )

        start_date = _format_date(
            item.get("start_date")
        )

        end_date = _format_date(
            item.get("end_date")
        )

        premise_address = _safe_text(
            item.get("premise_address")
        )

        mailing_address = _safe_text(
            item.get("mailing_address")
        )

        outstanding_rent = _safe_float(
            item.get("outstanding_rent")
        )

        current_rent = _safe_float(
            item.get("current_rent")
        )

        water_charge = _safe_float(
            item.get("water_charge")
        )

        electric_charge = _safe_float(
            item.get("electric_charge")
        )

        management_charge = _safe_float(
            item.get("management_charge")
        )

        amount = _safe_float(
            item.get("amount")
        )

        total_amount += amount

        premise_lines = _wrap_text_lines(
            c,
            premise_address,
            255,
            "Helvetica",
            8.5,
        )

        mailing_lines = _wrap_text_lines(
            c,
            mailing_address,
            255,
            "Helvetica",
            8.5,
        )

        optional_charge_count = sum(
            1
            for charge in [
                water_charge,
                electric_charge,
                management_charge,
            ]
            if charge > 0
        )

        old_account_extra = (
            25
            if old_account_number != "-"
            else 0
        )

        row_height = (
            255
            + old_account_extra
            + (len(premise_lines) * 11)
            + (len(mailing_lines) * 11)
            + (optional_charge_count * 25)
        )

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

        c.setFillColor(
            soft_blue
            if index % 2 == 0
            else colors.white
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

        c.setFillColor(dark_text)
        c.setFont("Helvetica-Bold", 10)

        c.drawString(
            table_left + 18,
            y - 23,
            str(index),
        )

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
            label_width=125,
            malay_size=8,
            english_size=7,
            value_size=8.5,
        )

        if old_account_number != "-":
            info_y -= 3

            info_y = _draw_bilingual_label_value(
                c,
                L["old_account_number_ms"],
                L["old_account_number_en"],
                old_account_number,
                table_left + 55,
                info_y,
                max_width=content_width,
                label_width=125,
                malay_size=8,
                english_size=7,
                value_size=8.5,
            )

        info_y -= 3

        info_y = _draw_bilingual_label_value(
            c,
            L["tenant_name_ms"],
            L["tenant_name_en"],
            tenant_name,
            table_left + 55,
            info_y,
            max_width=content_width,
            label_width=125,
            malay_size=8,
            english_size=7,
            value_size=8.5,
        )

        info_y -= 3

        info_y = _draw_bilingual_label_value(
            c,
            L["registration_no_ms"],
            L["registration_no_en"],
            registration_no,
            table_left + 55,
            info_y,
            max_width=content_width,
            label_width=125,
            malay_size=8,
            english_size=7,
            value_size=8.5,
        )

        info_y -= 3

        info_y = _draw_bilingual_label_value(
            c,
            L["rental_period_ms"],
            L["rental_period_en"],
            f"{start_date} - {end_date}",
            table_left + 55,
            info_y,
            max_width=content_width,
            label_width=125,
            malay_size=8,
            english_size=7,
            value_size=8.5,
        )

        info_y -= 4

        # Premise address
        c.setFillColor(primary_blue)
        c.setFont("Helvetica-Bold", 8)

        c.drawString(
            table_left + 55,
            info_y,
            L["premise_address_ms"],
        )

        c.setFillColor(grey_text)
        c.setFont("Helvetica-Oblique", 7)

        c.drawString(
            table_left + 55,
            info_y - 10,
            L["premise_address_en"],
        )

        info_y -= 24

        c.setFillColor(
            colors.HexColor("#333333")
        )

        c.setFont("Helvetica", 8.5)

        for line in premise_lines:
            c.drawString(
                table_left + 55,
                info_y,
                line,
            )

            info_y -= 11

        info_y -= 5

        # Mailing address
        c.setFillColor(primary_blue)
        c.setFont("Helvetica-Bold", 8)

        c.drawString(
            table_left + 55,
            info_y,
            L["mailing_address_ms"],
        )

        c.setFillColor(grey_text)
        c.setFont("Helvetica-Oblique", 7)

        c.drawString(
            table_left + 55,
            info_y - 10,
            L["mailing_address_en"],
        )

        info_y -= 24

        c.setFillColor(
            colors.HexColor("#333333")
        )

        c.setFont("Helvetica", 8.5)

        for line in mailing_lines:
            c.drawString(
                table_left + 55,
                info_y,
                line,
            )

            info_y -= 11

        info_y -= 8

        # Charges
        charge_rows = [
            (
                L["outstanding_rent_ms"],
                L["outstanding_rent_en"],
                outstanding_rent,
                True,
            ),
            (
                L["current_rent_ms"],
                L["current_rent_en"],
                current_rent,
                True,
            ),
            (
                L["water_charge_ms"],
                L["water_charge_en"],
                water_charge,
                water_charge > 0,
            ),
            (
                L["electric_charge_ms"],
                L["electric_charge_en"],
                electric_charge,
                electric_charge > 0,
            ),
            (
                L["management_charge_ms"],
                L["management_charge_en"],
                management_charge,
                management_charge > 0,
            ),
        ]

        for (
            malay_label,
            english_label,
            charge_value,
            should_show,
        ) in charge_rows:
            if not should_show:
                continue

            info_y = _draw_bilingual_label_value(
                c,
                malay_label,
                english_label,
                f"RM {_format_money(charge_value)}",
                table_left + 55,
                info_y,
                max_width=content_width,
                label_width=125,
                malay_size=8,
                english_size=7,
                value_size=8.5,
            )

            info_y -= 3

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
        L["total_paid_ms"],
        L["total_paid_en"],
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

    _draw_bilingual_wrapped_center(
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
    api_data_1 = {
        "module": "S",
        "account_no": "S0602000081401",
        "old_account_no": "",
        "name": "KUMARI A/P MUZHY",
        "invoice_no": "",
        "start_date": "2025-08-04",
        "end_date": "2025-08-31",
        "rental_fee": "100.000000",
        "rent_alamatswn": "NO. 1",
        "rent_jalanname": "DATARAN NIAGA KARAK",
        "rent_postcode": "",
        "rent_bandarnam": "KARAK",
        "rent_negeri": "",
        "rent_pdaftaran": "740717065068",
        "alamat1": "NO. 85,",
        "alamat2": "TAMAN KARAK INDAH",
        "alamat3": "",
        "alamat4": "",
        "postcode": "28600",
        "pekan_name": "KARAK",
        "ten_negeri": "",
        "telephone": "",
        "email": "",
        "tunggakan_sewa": "400.00",
        "sewa_semasa": "",
        "tunggakan_caj_air": "",
        "caj_air_semasa": "",
        "tunggakan_caj_elektrik": "",
        "caj_elektrik_semasa": "",
        "tunggakan_caj_pengurusan": "",
        "caj_pengurusan_semasa": "",
        "jumlah": "500.00",
        "jumlah_setahun": "1100.000000",
    }

    api_data_2 = {
        "account_no": "S0602000081402",
        "old_account_no": "",
        "name": "TEST TENANT",
        "start_date": "2025-09-01",
        "end_date": "2025-09-30",
        "rental_fee": "150.000000",
        "rent_alamatswn": "NO. 2",
        "rent_jalanname": "DATARAN NIAGA KARAK",
        "rent_postcode": "",
        "rent_bandarnam": "KARAK",
        "rent_negeri": "",
        "rent_pdaftaran": "800101015555",
        "alamat1": "NO. 10",
        "alamat2": "TAMAN CONTOH",
        "alamat3": "",
        "alamat4": "",
        "postcode": "28600",
        "pekan_name": "KARAK",
        "ten_negeri": "",
        "tunggakan_sewa": "150.00",
        "tunggakan_caj_air": "0",
        "tunggakan_caj_elektrik": "0",
        "tunggakan_caj_pengurusan": "0",
        "jumlah": "150.00",
    }

    sewaan_items = [
        build_sewaan_receipt_item_from_api(
            api_data_1
        ),
        build_sewaan_receipt_item_from_api(
            api_data_2
        ),
    ]

    pdf_bytes = generate_sewaan_receipt_bentong(
        paid_date=datetime.datetime.now(),
        payment_method="DuitNow QR",
        order_no="ORD123456",
        bank_trx_no="BANK987654",
        sewaan_items=sewaan_items,
    )

    with open(
        "sewaan_receipt_bentong.pdf",
        "wb",
    ) as output_file:
        output_file.write(pdf_bytes)

    print(
        "PDF generated: "
        "sewaan_receipt_bentong.pdf"
    )