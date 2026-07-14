from io import BytesIO
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


# =====================================================
# LOGO HANDLING
# =====================================================

LOGO_PATH = "app/resources/images/City_Car_Park_logo.png"
LOGO_RL = None

if os.path.exists(LOGO_PATH):
    try:
        with open(LOGO_PATH, "rb") as logo_file:
            LOGO_RL = ImageReader(
                BytesIO(logo_file.read())
            )

        print(
            "[INFO] Logo loaded for "
            "ReportLab multiple-license PDF"
        )

    except Exception as error:
        print(
            "[WARN] Failed to load "
            f"ReportLab logo: {error}"
        )

else:
    print(
        "[WARN] Logo path does not exist: "
        f"{LOGO_PATH}"
    )


# =====================================================
# HELPERS
# =====================================================

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


def _format_date(value):
    if not value:
        return "-"

    try:
        return value.strftime("%d/%m/%Y")
    except (AttributeError, ValueError):
        return _safe_text(value)


def _draw_image_keep_ratio(
    pdf,
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

        pdf.drawImage(
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
            "[WARN] Failed to draw logo: "
            f"{error}"
        )


def _draw_bilingual_left(
    pdf,
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
    pdf.setFillColor(malay_color)
    pdf.setFont(
        "Helvetica-Bold",
        malay_size,
    )

    pdf.drawString(
        x,
        y,
        str(malay),
    )

    pdf.setFillColor(english_color)
    pdf.setFont(
        "Helvetica-Oblique",
        english_size,
    )

    pdf.drawString(
        x,
        y - line_gap,
        str(english),
    )


def _draw_bilingual_right(
    pdf,
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
    pdf.setFillColor(malay_color)
    pdf.setFont(
        "Helvetica-Bold",
        malay_size,
    )

    pdf.drawRightString(
        x,
        y,
        str(malay),
    )

    pdf.setFillColor(english_color)
    pdf.setFont(
        "Helvetica-Oblique",
        english_size,
    )

    pdf.drawRightString(
        x,
        y - line_gap,
        str(english),
    )


def _draw_bilingual_center(
    pdf,
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
    pdf.setFillColor(malay_color)
    pdf.setFont(
        "Helvetica-Bold",
        malay_size,
    )

    pdf.drawCentredString(
        x,
        y,
        str(malay),
    )

    pdf.setFillColor(english_color)
    pdf.setFont(
        "Helvetica-Oblique",
        english_size,
    )

    pdf.drawCentredString(
        x,
        y - line_gap,
        str(english),
    )


# =====================================================
# BILINGUAL LABELS
# MALAY BOLD / ENGLISH ITALIC
# =====================================================

L = {
    "doc_title_ms": "RESIT PELBAGAI LESEN",
    "doc_title_en": "MULTIPLE LICENSE RECEIPT",

    "subtitle_ms": "Rekod Transaksi Rasmi",
    "subtitle_en": "Official Transaction Record",

    "col_number_ms": "No. Lesen",
    "col_number_en": "License Number",

    "col_type_ms": "Jenis Lesen",
    "col_type_en": "License Type",

    "col_expiry_ms": "Tarikh Luput",
    "col_expiry_en": "Expiry Date",

    "col_amount_ms": "Jumlah (RM)",
    "col_amount_en": "Amount (RM)",

    "total_ms": "Jumlah Keseluruhan",
    "total_en": "Total Amount",

    "thank_you_ms": (
        "Terima kasih atas pembayaran anda."
    ),

    "thank_you_en": (
        "Thank you for your payment."
    ),

    "footer_ms": (
        "2026 Juara Inovasi Pintar System "
        "· Hak Cipta Terpelihara"
    ),

    "footer_en": "All Rights Reserved",
}


# =====================================================
# PAGE HEADER
# =====================================================

def _draw_page_header(
    pdf,
    width,
    height,
    primary_blue,
    secondary_blue,
):
    header_height = 165

    pdf.setFillColor(primary_blue)

    pdf.rect(
        0,
        height - header_height,
        width,
        header_height,
        fill=True,
        stroke=False,
    )

    pdf.setFillColor(secondary_blue)

    pdf.rect(
        0,
        height - 42,
        width,
        42,
        fill=True,
        stroke=False,
    )

    # Decorative circles
    pdf.setFillColor(
        colors.Color(
            1,
            1,
            1,
            alpha=0.08,
        )
    )

    pdf.circle(
        width - 45,
        height - 50,
        95,
        fill=True,
        stroke=False,
    )

    pdf.circle(
        40,
        height - 145,
        55,
        fill=True,
        stroke=False,
    )

    if LOGO_RL:
        _draw_image_keep_ratio(
            pdf,
            LOGO_RL,
            40,
            height - 135,
            100,
            90,
        )

    _draw_bilingual_center(
        pdf,
        L["doc_title_ms"],
        L["doc_title_en"],
        width / 2,
        height - 62,
        malay_size=19,
        english_size=10,
        malay_color=colors.white,
        english_color=colors.white,
        line_gap=15,
    )

    _draw_bilingual_center(
        pdf,
        L["subtitle_ms"],
        L["subtitle_en"],
        width / 2,
        height - 108,
        malay_size=9,
        english_size=8,
        malay_color=colors.white,
        english_color=colors.white,
        line_gap=11,
    )

    return height - header_height - 28


# =====================================================
# TABLE HEADER
# =====================================================

def _draw_table_header(
    pdf,
    y,
    table_left,
    table_width,
    secondary_blue,
):
    header_height = 44

    pdf.setFillColor(secondary_blue)

    pdf.roundRect(
        table_left,
        y - header_height,
        table_width,
        header_height,
        10,
        fill=True,
        stroke=False,
    )

    col_x = {
        "number": table_left + 14,
        "type": table_left + 170,
        "expiry": table_left + 330,
        "amount": table_left + table_width - 14,
    }

    _draw_bilingual_left(
        pdf,
        L["col_number_ms"],
        L["col_number_en"],
        col_x["number"],
        y - 15,
        malay_size=8.5,
        english_size=7.5,
        malay_color=colors.white,
        english_color=colors.white,
        line_gap=11,
    )

    _draw_bilingual_left(
        pdf,
        L["col_type_ms"],
        L["col_type_en"],
        col_x["type"],
        y - 15,
        malay_size=8.5,
        english_size=7.5,
        malay_color=colors.white,
        english_color=colors.white,
        line_gap=11,
    )

    _draw_bilingual_left(
        pdf,
        L["col_expiry_ms"],
        L["col_expiry_en"],
        col_x["expiry"],
        y - 15,
        malay_size=8.5,
        english_size=7.5,
        malay_color=colors.white,
        english_color=colors.white,
        line_gap=11,
    )

    _draw_bilingual_right(
        pdf,
        L["col_amount_ms"],
        L["col_amount_en"],
        col_x["amount"],
        y - 15,
        malay_size=8.5,
        english_size=7.5,
        malay_color=colors.white,
        english_color=colors.white,
        line_gap=11,
    )

    return y - header_height - 6


# =====================================================
# FOOTER
# =====================================================

def _draw_footer(
    pdf,
    width,
    primary_blue,
    grey_text,
):
    pdf.setStrokeColor(
        colors.HexColor("#DCE8F8")
    )

    pdf.line(
        40,
        55,
        width - 40,
        55,
    )

    _draw_bilingual_center(
        pdf,
        L["footer_ms"],
        L["footer_en"],
        width / 2,
        39,
        malay_size=7.5,
        english_size=6.5,
        malay_color=primary_blue,
        english_color=grey_text,
        line_gap=9,
    )


# =====================================================
# MULTIPLE LICENSE RECEIPT PDF
# =====================================================

def generate_multi_license_pdf(
    Licenses,
    total_amount,
):
    """
    Generate a modern bilingual multiple-license PDF.

    Bahasa Melayu is bold.
    English is italic underneath.
    """

    buffer = BytesIO()

    pdf = canvas.Canvas(
        buffer,
        pagesize=A4,
    )

    width, height = A4

    primary_blue = colors.HexColor("#003B8E")
    secondary_blue = colors.HexColor("#0A66D8")
    soft_blue = colors.HexColor("#F4F8FF")
    row_blue = colors.HexColor("#EDF4FF")
    border_color = colors.HexColor("#DCE8F8")
    grey_text = colors.HexColor("#6B7280")
    dark_text = colors.HexColor("#111827")
    success_green = colors.HexColor("#15803D")

    table_left = 40
    table_width = width - 80
    row_height = 32
    footer_safe_y = 95

    safe_total = _safe_amount(
        total_amount
    )

    # =================================================
    # FIRST PAGE HEADER
    # =================================================

    y = _draw_page_header(
        pdf,
        width,
        height,
        primary_blue,
        secondary_blue,
    )

    y = _draw_table_header(
        pdf,
        y,
        table_left,
        table_width,
        secondary_blue,
    )

    # =================================================
    # TABLE ROWS
    # =================================================

    for index, license_item in enumerate(
        Licenses,
        start=1,
    ):
        if y - row_height < footer_safe_y:
            _draw_footer(
                pdf,
                width,
                primary_blue,
                grey_text,
            )

            pdf.showPage()

            y = _draw_page_header(
                pdf,
                width,
                height,
                primary_blue,
                secondary_blue,
            )

            y = _draw_table_header(
                pdf,
                y,
                table_left,
                table_width,
                secondary_blue,
            )

        license_number = _safe_text(
            license_item.get(
                "licensenumber"
            )
        )

        license_type = _safe_text(
            license_item.get(
                "licensetype"
            )
        )

        expiry_date = _format_date(
            license_item.get(
                "expired_date"
            )
        )

        amount = _safe_amount(
            license_item.get(
                "amount"
            )
        )

        row_background = (
            row_blue
            if index % 2 == 0
            else colors.white
        )

        pdf.setFillColor(
            row_background
        )

        pdf.setStrokeColor(
            border_color
        )

        pdf.roundRect(
            table_left,
            y - row_height,
            table_width,
            row_height,
            7,
            fill=True,
            stroke=True,
        )

        pdf.setFillColor(
            dark_text
        )

        pdf.setFont(
            "Helvetica-Bold",
            9.5,
        )

        pdf.drawString(
            table_left + 14,
            y - 20,
            license_number,
        )

        pdf.setFont(
            "Helvetica",
            9,
        )

        pdf.drawString(
            table_left + 170,
            y - 20,
            license_type,
        )

        pdf.drawString(
            table_left + 330,
            y - 20,
            expiry_date,
        )

        pdf.setFillColor(
            primary_blue
        )

        pdf.setFont(
            "Helvetica-Bold",
            9.5,
        )

        pdf.drawRightString(
            table_left + table_width - 14,
            y - 20,
            f"{amount:,.2f}",
        )

        y -= row_height + 5

    # =================================================
    # TOTAL SECTION
    # =================================================

    total_height = 58
    thank_you_space = 65

    if (
        y
        - total_height
        - thank_you_space
        < footer_safe_y
    ):
        _draw_footer(
            pdf,
            width,
            primary_blue,
            grey_text,
        )

        pdf.showPage()

        y = _draw_page_header(
            pdf,
            width,
            height,
            primary_blue,
            secondary_blue,
        )

    y -= 16

    pdf.setFillColor(
        soft_blue
    )

    pdf.setStrokeColor(
        colors.HexColor("#BFD7FF")
    )

    pdf.roundRect(
        table_left,
        y - total_height,
        table_width,
        total_height,
        12,
        fill=True,
        stroke=True,
    )

    _draw_bilingual_left(
        pdf,
        L["total_ms"],
        L["total_en"],
        table_left + 18,
        y - 22,
        malay_size=12,
        english_size=8.5,
        malay_color=primary_blue,
        english_color=grey_text,
        line_gap=12,
    )

    pdf.setFillColor(
        secondary_blue
    )

    pdf.setFont(
        "Helvetica-Bold",
        20,
    )

    pdf.drawRightString(
        table_left + table_width - 18,
        y - 35,
        f"RM {safe_total:,.2f}",
    )

    y -= total_height + 30

    # =================================================
    # THANK YOU
    # =================================================

    _draw_bilingual_center(
        pdf,
        L["thank_you_ms"],
        L["thank_you_en"],
        width / 2,
        y,
        malay_size=11,
        english_size=8.5,
        malay_color=success_green,
        english_color=success_green,
        line_gap=12,
    )

    # =================================================
    # FOOTER
    # =================================================

    _draw_footer(
        pdf,
        width,
        primary_blue,
        grey_text,
    )

    pdf.save()

    buffer.seek(0)

    return buffer