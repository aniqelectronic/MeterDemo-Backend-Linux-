from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from io import BytesIO
from datetime import datetime
import os

from app.utils.sirim_time import sirim_now_naive


# =========================================================
# LOGO PRELOAD
# =========================================================

LOGO = None
LOGO_PATH = "app/resources/images/City_Car_Park_logo.png"

try:
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as logo_file:
            LOGO = ImageReader(
                BytesIO(logo_file.read())
            )

        print("[INFO] Logo preloaded successfully.")

    else:
        print(
            f"[WARN] Logo not found at: "
            f"{LOGO_PATH}"
        )

except Exception as error:
    print(
        f"[WARN] Failed to load logo: "
        f"{error}"
    )


# =========================================================
# HELPERS
# =========================================================

def _safe_text(value, fallback="-"):
    if value is None:
        return fallback

    text = str(value).strip()

    return text if text else fallback


def _safe_amount(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _format_hours(value):
    try:
        hours = float(value or 0)
        return f"{hours:.2f}"
    except (TypeError, ValueError):
        return "0.00"


def _format_datetime(value):
    if not value:
        return "-"

    try:
        return (
            value
            .replace(
                second=0,
                microsecond=0,
            )
            .strftime(
                "%d/%m/%Y %I:%M %p"
            )
        )

    except (AttributeError, ValueError):
        return _safe_text(value)


def _draw_image_keep_ratio(
    c,
    image,
    x,
    y,
    max_width,
    max_height,
):
    try:
        image_width, image_height = image.getSize()

        ratio = min(
            max_width / image_width,
            max_height / image_height,
        )

        draw_width = image_width * ratio
        draw_height = image_height * ratio

        c.drawImage(
            image,
            x + (max_width - draw_width) / 2,
            y + (max_height - draw_height) / 2,
            width=draw_width,
            height=draw_height,
            preserveAspectRatio=True,
            mask="auto",
        )

    except Exception as error:
        print(
            f"[WARN] Failed to draw logo: "
            f"{error}"
        )


def _draw_bilingual_left(
    c,
    malay,
    english,
    x,
    y,
    malay_size=9,
    english_size=8,
    malay_color=colors.black,
    english_color=colors.HexColor("#6B7280"),
    line_gap=11,
):
    c.setFillColor(malay_color)
    c.setFont(
        "Helvetica-Bold",
        malay_size,
    )
    c.drawString(
        x,
        y,
        str(malay),
    )

    c.setFillColor(english_color)
    c.setFont(
        "Helvetica-Oblique",
        english_size,
    )
    c.drawString(
        x,
        y - line_gap,
        str(english),
    )


def _draw_bilingual_center(
    c,
    malay,
    english,
    x,
    y,
    malay_size=9,
    english_size=8,
    malay_color=colors.black,
    english_color=colors.HexColor("#6B7280"),
    line_gap=11,
):
    c.setFillColor(malay_color)
    c.setFont(
        "Helvetica-Bold",
        malay_size,
    )
    c.drawCentredString(
        x,
        y,
        str(malay),
    )

    c.setFillColor(english_color)
    c.setFont(
        "Helvetica-Oblique",
        english_size,
    )
    c.drawCentredString(
        x,
        y - line_gap,
        str(english),
    )


def _draw_info_card(
    c,
    x,
    y,
    width,
    height,
    malay_label,
    english_label,
    value,
    primary_blue,
    card_background,
    border_color,
    value_size=11,
):
    c.setFillColor(card_background)
    c.setStrokeColor(border_color)

    c.roundRect(
        x,
        y,
        width,
        height,
        10,
        fill=True,
        stroke=True,
    )

    _draw_bilingual_left(
        c,
        malay_label,
        english_label,
        x + 14,
        y + height - 19,
        malay_size=8.5,
        english_size=7,
        malay_color=primary_blue,
        english_color=colors.HexColor("#6B7280"),
        line_gap=10,
    )

    c.setFillColor(
        colors.HexColor("#111827")
    )
    c.setFont(
        "Helvetica-Bold",
        value_size,
    )

    c.drawString(
        x + 14,
        y + 15,
        _safe_text(value),
    )


# =========================================================
# BILINGUAL LABELS
# MALAY BOLD / ENGLISH ITALIC
# =========================================================

L = {
    "doc_title_ms": "E-RESIT PARKIR",
    "doc_title_en": "PARKING E-RECEIPT",

    "generated_ms": "Dijana pada",
    "generated_en": "Generated at",

    "ticket_id_ms": "ID Tiket",
    "ticket_id_en": "Ticket ID",

    "plate_ms": "Nombor Plat",
    "plate_en": "Plate Number",

    "duration_ms": "Tempoh Parkir",
    "duration_en": "Parking Duration",

    "time_in_ms": "Waktu Mula",
    "time_in_en": "Time In",

    "time_out_ms": "Waktu Tamat",
    "time_out_en": "Time Out",

    "transaction_type_ms": "Jenis Transaksi",
    "transaction_type_en": "Transaction Type",

    "order_no_ms": "No. Pesanan",
    "order_no_en": "Order No.",

    "bank_trx_ms": "No. Transaksi Bank",
    "bank_trx_en": "Bank Transaction No.",

    "amount_paid_ms": "Jumlah Dibayar",
    "amount_paid_en": "Total Paid",

    "thanks_ms": (
        "Terima kasih kerana menggunakan "
        "perkhidmatan parkir kami."
    ),

    "thanks_en": (
        "Thank you for using our parking service."
    ),

    "safe_ms": "Pandu dengan selamat!",
    "safe_en": "Drive safely!",

    "company_ms": "Juara Inovasi Pasifik System",
    "company_en": "All Rights Reserved",
}


# =========================================================
# PARKING RECEIPT GENERATOR
# =========================================================

def generate_parking_receipt(
    ticket_id: str,
    plate: str,
    hours: float,
    time_in: datetime,
    time_out: datetime,
    amount: float,
    transaction_type: str,
    order_no: str = None,
    bank_trx_no: str = None,
):
    """
    Generate a polished bilingual parking receipt.

    Bahasa Melayu is bold.
    English is italic below the Malay label.
    """

    buffer = BytesIO()

    c = canvas.Canvas(
        buffer,
        pagesize=A4,
    )

    width, height = A4

    # =====================================================
    # COLORS
    # =====================================================

    primary_blue = colors.HexColor("#003B8E")
    secondary_blue = colors.HexColor("#0A66D8")
    accent_blue = colors.HexColor("#EAF3FF")
    card_background = colors.HexColor("#F8FBFF")
    border_color = colors.HexColor("#DCE8F8")
    grey_text = colors.HexColor("#6B7280")
    dark_text = colors.HexColor("#111827")
    success_green = colors.HexColor("#15803D")

    # =====================================================
    # HEADER
    # =====================================================

    header_height = 170

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
        height - 42,
        width,
        42,
        fill=True,
        stroke=False,
    )

    # Decorative circles
    c.setFillColor(
        colors.Color(
            1,
            1,
            1,
            alpha=0.08,
        )
    )

    c.circle(
        width - 40,
        height - 45,
        95,
        fill=True,
        stroke=False,
    )

    c.circle(
        40,
        height - 145,
        55,
        fill=True,
        stroke=False,
    )

    if LOGO:
        _draw_image_keep_ratio(
            c,
            LOGO,
            40,
            height - 135,
            100,
            90,
        )

    _draw_bilingual_center(
        c,
        L["doc_title_ms"],
        L["doc_title_en"],
        width / 2,
        height - 62,
        malay_size=20,
        english_size=11,
        malay_color=colors.white,
        english_color=colors.white,
        line_gap=15,
    )

    _draw_bilingual_center(
        c,
        L["generated_ms"],
        L["generated_en"],
        width / 2,
        height - 105,
        malay_size=8,
        english_size=7,
        malay_color=colors.white,
        english_color=colors.white,
        line_gap=10,
    )

    c.setFillColor(colors.white)
    c.setFont(
        "Helvetica",
        9,
    )

    c.drawCentredString(
        width / 2,
        height - 128,
        sirim_now_naive().strftime(
            "%d %b %Y, %I:%M %p"
        ),
    )

    # =====================================================
    # MAIN CONTENT
    # =====================================================

    content_left = 45
    content_right = width - 45
    content_width = (
        content_right - content_left
    )

    y = height - 210

    gap = 12
    card_height = 66
    card_width = (
        content_width - gap
    ) / 2

    # Row 1
    _draw_info_card(
        c,
        content_left,
        y - card_height,
        card_width,
        card_height,
        L["ticket_id_ms"],
        L["ticket_id_en"],
        ticket_id,
        primary_blue,
        card_background,
        border_color,
    )

    _draw_info_card(
        c,
        content_left + card_width + gap,
        y - card_height,
        card_width,
        card_height,
        L["plate_ms"],
        L["plate_en"],
        plate,
        primary_blue,
        card_background,
        border_color,
    )

    y -= card_height + gap

    # Row 2
    _draw_info_card(
        c,
        content_left,
        y - card_height,
        card_width,
        card_height,
        L["duration_ms"],
        L["duration_en"],
        f"{_format_hours(hours)} jam",
        primary_blue,
        card_background,
        border_color,
    )

    _draw_info_card(
        c,
        content_left + card_width + gap,
        y - card_height,
        card_width,
        card_height,
        L["transaction_type_ms"],
        L["transaction_type_en"],
        _safe_text(
            transaction_type
        ).title(),
        primary_blue,
        card_background,
        border_color,
    )

    y -= card_height + gap

    # Row 3
    _draw_info_card(
        c,
        content_left,
        y - card_height,
        card_width,
        card_height,
        L["time_in_ms"],
        L["time_in_en"],
        _format_datetime(time_in),
        primary_blue,
        card_background,
        border_color,
        value_size=9.5,
    )

    _draw_info_card(
        c,
        content_left + card_width + gap,
        y - card_height,
        card_width,
        card_height,
        L["time_out_ms"],
        L["time_out_en"],
        _format_datetime(time_out),
        primary_blue,
        card_background,
        border_color,
        value_size=9.5,
    )

    y -= card_height + gap

    # Row 4
    _draw_info_card(
        c,
        content_left,
        y - card_height,
        card_width,
        card_height,
        L["order_no_ms"],
        L["order_no_en"],
        order_no,
        primary_blue,
        card_background,
        border_color,
        value_size=9.5,
    )

    _draw_info_card(
        c,
        content_left + card_width + gap,
        y - card_height,
        card_width,
        card_height,
        L["bank_trx_ms"],
        L["bank_trx_en"],
        bank_trx_no,
        primary_blue,
        card_background,
        border_color,
        value_size=9.5,
    )

    y -= card_height + 22

    # =====================================================
    # TOTAL SECTION
    # =====================================================

    total_height = 72

    c.setFillColor(accent_blue)
    c.setStrokeColor(
        colors.HexColor("#BFD7FF")
    )

    c.roundRect(
        content_left,
        y - total_height,
        content_width,
        total_height,
        14,
        fill=True,
        stroke=True,
    )

    _draw_bilingual_left(
        c,
        L["amount_paid_ms"],
        L["amount_paid_en"],
        content_left + 20,
        y - 25,
        malay_size=13,
        english_size=9,
        malay_color=primary_blue,
        english_color=grey_text,
        line_gap=13,
    )

    c.setFillColor(secondary_blue)
    c.setFont(
        "Helvetica-Bold",
        24,
    )

    c.drawRightString(
        content_right - 20,
        y - 42,
        f"RM {_safe_amount(amount):,.2f}",
    )

    y -= total_height + 30

    # =====================================================
    # THANK YOU SECTION
    # =====================================================

    _draw_bilingual_center(
        c,
        L["thanks_ms"],
        L["thanks_en"],
        width / 2,
        y,
        malay_size=11,
        english_size=8.5,
        malay_color=success_green,
        english_color=success_green,
        line_gap=12,
    )

    _draw_bilingual_center(
        c,
        L["safe_ms"],
        L["safe_en"],
        width / 2,
        y - 32,
        malay_size=12,
        english_size=9,
        malay_color=success_green,
        english_color=success_green,
        line_gap=12,
    )

    # =====================================================
    # FOOTER
    # =====================================================

    c.setStrokeColor(border_color)

    c.line(
        45,
        70,
        width - 45,
        70,
    )

    _draw_bilingual_center(
        c,
        L["company_ms"],
        L["company_en"],
        width / 2,
        52,
        malay_size=8,
        english_size=7,
        malay_color=dark_text,
        english_color=grey_text,
        line_gap=10,
    )

    c.setFillColor(grey_text)
    c.setFont(
        "Helvetica",
        7,
    )

    c.drawCentredString(
        width / 2,
        28,
        "© 2026 Juara Inovasi Pasifik System",
    )

    # =====================================================
    # FINALIZE
    # =====================================================

    c.showPage()
    c.save()

    buffer.seek(0)

    return buffer.read()