from io import BytesIO
import os

from fpdf import FPDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from app.utils.blob_upload import upload_to_blob


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
            "ReportLab compound PDF"
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

def safe_text(value, fallback="-"):
    if value is None:
        return fallback

    text = str(value).strip()

    return text if text else fallback


def safe_date(value):
    if value is None:
        return "-"

    try:
        return value.strftime("%d/%m/%Y")
    except (AttributeError, ValueError):
        return safe_text(value)


def safe_time(value):
    if value is None:
        return "-"

    try:
        return value.strftime("%I:%M %p")
    except (AttributeError, ValueError):
        return safe_text(value)


def safe_amount(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


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

LABELS = {
    "single_title_ms": "E-RESIT KOMPAUN",
    "single_title_en": "COMPOUND E-RECEIPT",

    "single_details_ms": "Butiran Resit",
    "single_details_en": "Receipt Details",

    "name_ms": "Nama",
    "name_en": "Name",

    "compound_no_ms": "No. Kompaun",
    "compound_no_en": "Compound No.",

    "plate_no_ms": "No. Plat",
    "plate_no_en": "Plate No.",

    "date_ms": "Tarikh",
    "date_en": "Date",

    "time_ms": "Masa",
    "time_en": "Time",

    "offense_ms": "Kesalahan",
    "offense_en": "Offense",

    "amount_ms": "Jumlah Dibayar",
    "amount_en": "Total Paid",

    "multi_title_ms": "RESIT PELBAGAI KOMPAUN",
    "multi_title_en": "MULTIPLE COMPOUND RECEIPT",

    "subtitle_ms": "Rekod Transaksi Rasmi",
    "subtitle_en": "Official Transaction Record",

    "column_compound_no_ms": "No. Kompaun",
    "column_compound_no_en": "Compound Number",

    "column_amount_ms": "Jumlah (RM)",
    "column_amount_en": "Amount (RM)",

    "total_ms": "Jumlah Keseluruhan",
    "total_en": "Total Amount",

    "thank_you_ms": "Terima kasih atas pembayaran anda!",
    "thank_you_en": "Thank you for your payment!",

    "footer_ms": (
        "2026 Juara Inovasi Pasifik System "
        "· Hak Cipta Terpelihara"
    ),

    "footer_en": "All Rights Reserved",
}


# =====================================================
# SINGLE COMPOUND RECEIPT PDF
# FPDF 1.x SAFE
# =====================================================

def generate_single_compound_pdf(compound):
    """
    Generate and upload a polished bilingual single-compound PDF.

    Returns:
        str: Uploaded PDF Blob URL.
    """

    compound_name = safe_text(compound.name)
    compound_no = safe_text(compound.compoundnum)
    compound_plate = safe_text(compound.plate)
    compound_date = safe_date(compound.date)
    compound_time = safe_time(compound.time)
    compound_offense = safe_text(compound.offense)
    compound_amount = safe_amount(compound.amount)

    pdf = FPDF()
    pdf.add_page()

    # =================================================
    # COLORS
    # =================================================

    primary_blue = (0, 59, 142)
    secondary_blue = (10, 102, 216)
    soft_blue = (234, 243, 255)
    card_blue = (248, 251, 255)
    grey = (107, 114, 128)
    dark = (17, 24, 39)
    green = (21, 128, 61)

    # =================================================
    # HEADER
    # =================================================

    pdf.set_fill_color(*primary_blue)
    pdf.rect(
        0,
        0,
        210,
        62,
        style="F",
    )

    pdf.set_fill_color(*secondary_blue)
    pdf.rect(
        0,
        0,
        210,
        10,
        style="F",
    )

    if os.path.exists(LOGO_PATH):
        try:
            pdf.image(
                LOGO_PATH,
                x=15,
                y=15,
                w=38,
            )
        except Exception as error:
            print(
                "[WARN] Failed to draw FPDF logo: "
                f"{error}"
            )

    pdf.set_text_color(255, 255, 255)

    pdf.set_xy(10, 18)
    pdf.set_font("Arial", "B", 18)

    pdf.cell(
        190,
        9,
        LABELS["single_title_ms"],
        align="C",
    )

    pdf.set_xy(10, 28)
    pdf.set_font("Arial", "I", 10)

    pdf.cell(
        190,
        7,
        LABELS["single_title_en"],
        align="C",
    )

    pdf.set_xy(10, 42)
    pdf.set_font("Arial", "B", 9)

    pdf.cell(
        190,
        6,
        LABELS["single_details_ms"],
        align="C",
    )

    pdf.set_xy(10, 49)
    pdf.set_font("Arial", "I", 8)

    pdf.cell(
        190,
        5,
        LABELS["single_details_en"],
        align="C",
    )

    # =================================================
    # DETAILS CARDS
    # =================================================

    pdf.set_text_color(*dark)

    card_x = 15
    card_w = 180
    card_h = 22
    y = 72

    details = [
        (
            LABELS["name_ms"],
            LABELS["name_en"],
            compound_name,
        ),
        (
            LABELS["compound_no_ms"],
            LABELS["compound_no_en"],
            compound_no,
        ),
        (
            LABELS["plate_no_ms"],
            LABELS["plate_no_en"],
            compound_plate,
        ),
        (
            LABELS["date_ms"],
            LABELS["date_en"],
            compound_date,
        ),
        (
            LABELS["time_ms"],
            LABELS["time_en"],
            compound_time,
        ),
    ]

    for index, (malay, english, value) in enumerate(details):
        if index % 2 == 0:
            pdf.set_fill_color(*card_blue)
        else:
            pdf.set_fill_color(255, 255, 255)

        pdf.set_draw_color(220, 232, 248)

        pdf.rounded_rect(
            card_x,
            y,
            card_w,
            card_h,
            3,
            style="DF",
        )

        pdf.set_xy(card_x + 6, y + 4)
        pdf.set_font("Arial", "B", 9)
        pdf.set_text_color(*primary_blue)

        pdf.cell(
            58,
            5,
            malay,
        )

        pdf.set_xy(card_x + 6, y + 10)
        pdf.set_font("Arial", "I", 7)
        pdf.set_text_color(*grey)

        pdf.cell(
            58,
            5,
            english,
        )

        pdf.set_xy(card_x + 68, y + 7)
        pdf.set_font("Arial", "B", 10)
        pdf.set_text_color(*dark)

        pdf.cell(
            105,
            7,
            value,
        )

        y += card_h + 3

    # =================================================
    # OFFENSE CARD
    # =================================================

    offense_h = 42

    pdf.set_fill_color(*card_blue)
    pdf.set_draw_color(220, 232, 248)

    pdf.rounded_rect(
        card_x,
        y,
        card_w,
        offense_h,
        3,
        style="DF",
    )

    pdf.set_xy(card_x + 6, y + 5)
    pdf.set_font("Arial", "B", 9)
    pdf.set_text_color(*primary_blue)

    pdf.cell(
        60,
        5,
        LABELS["offense_ms"],
    )

    pdf.set_xy(card_x + 6, y + 11)
    pdf.set_font("Arial", "I", 7)
    pdf.set_text_color(*grey)

    pdf.cell(
        60,
        5,
        LABELS["offense_en"],
    )

    pdf.set_xy(card_x + 68, y + 6)
    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(*dark)

    pdf.multi_cell(
        105,
        5,
        compound_offense,
    )

    y += offense_h + 8

    # =================================================
    # TOTAL CARD
    # =================================================

    pdf.set_fill_color(*soft_blue)
    pdf.set_draw_color(191, 215, 255)

    pdf.rounded_rect(
        card_x,
        y,
        card_w,
        28,
        4,
        style="DF",
    )

    pdf.set_xy(card_x + 8, y + 5)
    pdf.set_font("Arial", "B", 11)
    pdf.set_text_color(*primary_blue)

    pdf.cell(
        90,
        6,
        LABELS["amount_ms"],
    )

    pdf.set_xy(card_x + 8, y + 12)
    pdf.set_font("Arial", "I", 8)
    pdf.set_text_color(*grey)

    pdf.cell(
        90,
        5,
        LABELS["amount_en"],
    )

    pdf.set_xy(card_x + 105, y + 8)
    pdf.set_font("Arial", "B", 17)
    pdf.set_text_color(*secondary_blue)

    pdf.cell(
        62,
        10,
        f"RM {compound_amount:,.2f}",
        align="R",
    )

    # =================================================
    # THANK YOU
    # =================================================

    y += 40

    pdf.set_text_color(*green)
    pdf.set_xy(10, y)
    pdf.set_font("Arial", "B", 11)

    pdf.cell(
        190,
        7,
        LABELS["thank_you_ms"],
        align="C",
    )

    pdf.set_xy(10, y + 8)
    pdf.set_font("Arial", "I", 9)

    pdf.cell(
        190,
        6,
        LABELS["thank_you_en"],
        align="C",
    )

    # =================================================
    # FOOTER
    # =================================================

    pdf.set_draw_color(220, 232, 248)
    pdf.line(
        20,
        276,
        190,
        276,
    )

    pdf.set_text_color(*primary_blue)
    pdf.set_xy(10, 279)
    pdf.set_font("Arial", "B", 8)

    pdf.cell(
        190,
        5,
        LABELS["footer_ms"],
        align="C",
    )

    pdf.set_text_color(*grey)
    pdf.set_xy(10, 285)
    pdf.set_font("Arial", "I", 7)

    pdf.cell(
        190,
        5,
        LABELS["footer_en"],
        align="C",
    )

    # =================================================
    # OUTPUT
    # =================================================

    pdf_bytes = (
        pdf.output(dest="S")
        .encode("latin1")
    )

    filename = (
        f"compound_{compound_no}.pdf"
    )

    return upload_to_blob(
        filename,
        pdf_bytes,
        "application/pdf",
    )


# =====================================================
# MULTIPLE COMPOUND PDF HELPERS
# =====================================================

def draw_multi_compound_header(
    pdf,
    width,
    height,
):
    primary_blue = colors.HexColor("#003B8E")
    secondary_blue = colors.HexColor("#0A66D8")

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
        LABELS["multi_title_ms"],
        LABELS["multi_title_en"],
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
        LABELS["subtitle_ms"],
        LABELS["subtitle_en"],
        width / 2,
        height - 108,
        malay_size=9,
        english_size=8,
        malay_color=colors.white,
        english_color=colors.white,
        line_gap=11,
    )

    return height - header_height - 28


def draw_multi_compound_table_header(
    pdf,
    y,
):
    table_x = 40
    table_width = 520
    header_height = 44

    secondary_blue = colors.HexColor("#0A66D8")

    pdf.setFillColor(secondary_blue)

    pdf.roundRect(
        table_x,
        y - header_height,
        table_width,
        header_height,
        10,
        fill=True,
        stroke=False,
    )

    _draw_bilingual_left(
        pdf,
        LABELS["column_compound_no_ms"],
        LABELS["column_compound_no_en"],
        54,
        y - 15,
        malay_size=8.5,
        english_size=7.5,
        malay_color=colors.white,
        english_color=colors.white,
        line_gap=11,
    )

    _draw_bilingual_right(
        pdf,
        LABELS["column_amount_ms"],
        LABELS["column_amount_en"],
        546,
        y - 15,
        malay_size=8.5,
        english_size=7.5,
        malay_color=colors.white,
        english_color=colors.white,
        line_gap=11,
    )

    return y - header_height - 6


def draw_multi_compound_footer(
    pdf,
    width,
):
    primary_blue = colors.HexColor("#003B8E")
    grey_text = colors.HexColor("#6B7280")

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
        LABELS["footer_ms"],
        LABELS["footer_en"],
        width / 2,
        39,
        malay_size=7.5,
        english_size=6.5,
        malay_color=primary_blue,
        english_color=grey_text,
        line_gap=9,
    )


# =====================================================
# MULTIPLE COMPOUND RECEIPT PDF
# =====================================================

def generate_multi_compound_pdf(
    compounds,
    total_amount,
):
    """
    Generate a polished bilingual multiple-compound PDF.

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

    row_height = 34
    footer_safe_y = 95

    safe_total = safe_amount(
        total_amount
    )

    y = draw_multi_compound_header(
        pdf,
        width,
        height,
    )

    y = draw_multi_compound_table_header(
        pdf,
        y,
    )

    # =================================================
    # TABLE ROWS
    # =================================================

    for index, compound in enumerate(
        compounds,
        start=1,
    ):
        if y - row_height < footer_safe_y:
            draw_multi_compound_footer(
                pdf,
                width,
            )

            pdf.showPage()

            y = draw_multi_compound_header(
                pdf,
                width,
                height,
            )

            y = draw_multi_compound_table_header(
                pdf,
                y,
            )

        compound_number = safe_text(
            compound.get("compoundnum")
        )

        amount = safe_amount(
            compound.get("amount")
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
            40,
            y - row_height,
            520,
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
            10,
        )

        pdf.drawString(
            54,
            y - 22,
            compound_number,
        )

        pdf.setFillColor(
            primary_blue
        )

        pdf.setFont(
            "Helvetica-Bold",
            10,
        )

        pdf.drawRightString(
            546,
            y - 22,
            f"{amount:,.2f}",
        )

        y -= row_height + 5

    # =================================================
    # TOTAL
    # =================================================

    total_height = 58
    thank_you_space = 65

    if (
        y
        - total_height
        - thank_you_space
        < footer_safe_y
    ):
        draw_multi_compound_footer(
            pdf,
            width,
        )

        pdf.showPage()

        y = draw_multi_compound_header(
            pdf,
            width,
            height,
        )

    y -= 16

    pdf.setFillColor(
        soft_blue
    )

    pdf.setStrokeColor(
        colors.HexColor("#BFD7FF")
    )

    pdf.roundRect(
        40,
        y - total_height,
        520,
        total_height,
        12,
        fill=True,
        stroke=True,
    )

    _draw_bilingual_left(
        pdf,
        LABELS["total_ms"],
        LABELS["total_en"],
        58,
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
        542,
        y - 35,
        f"RM {safe_total:,.2f}",
    )

    y -= total_height + 30

    # =================================================
    # THANK YOU
    # =================================================

    _draw_bilingual_center(
        pdf,
        LABELS["thank_you_ms"],
        LABELS["thank_you_en"],
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

    draw_multi_compound_footer(
        pdf,
        width,
    )

    pdf.save()

    buffer.seek(0)

    return buffer