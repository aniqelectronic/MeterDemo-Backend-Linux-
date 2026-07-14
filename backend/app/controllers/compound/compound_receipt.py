from fpdf import FPDF
from app.utils.blob_upload import upload_to_blob
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
import os


# =====================================================
# LOGO HANDLING
# =====================================================

LOGO_PATH = "app/resources/images/City_Car_Park_logo.png"

LOGO_RL = None

if os.path.exists(LOGO_PATH):
    try:
        with open(LOGO_PATH, "rb") as logo_file:
            LOGO_RL = ImageReader(BytesIO(logo_file.read()))

        print("[INFO] Logo loaded for ReportLab multiple compound PDF")

    except Exception as error:
        print(f"[WARN] Failed to load ReportLab logo: {error}")

else:
    print(f"[WARN] Logo path does not exist: {LOGO_PATH}")


# =====================================================
# BILINGUAL LABELS
# BAHASA MELAYU / ENGLISH
# =====================================================

LABELS = {
    "single_title": "E-RESIT KOMPAUN / COMPOUND E-RECEIPT",
    "single_details": "Butiran Resit / Receipt Details",

    "name": "Nama / Name",
    "compound_no": "No. Kompaun / Compound No.",
    "plate_no": "No. Plat / Plate No.",
    "date": "Tarikh / Date",
    "time": "Masa / Time",
    "offense": "Kesalahan / Offense",
    "amount": "Jumlah / Amount",

    "multi_title": "RESIT PELBAGAI KOMPAUN / MULTIPLE COMPOUND RECEIPT",
    "subtitle": "Rekod Transaksi Rasmi / Official Transaction Record",

    "column_compound_no_ms": "No. Kompaun",
    "column_compound_no_en": "Compound Number",

    "column_amount_ms": "Jumlah (RM)",
    "column_amount_en": "Amount (RM)",

    "total": "JUMLAH KESELURUHAN / TOTAL AMOUNT:",

    "thank_you_ms": "Terima kasih atas pembayaran anda!",
    "thank_you_en": "Thank you for your payment!",

    "footer": (
        "2025 City Car Park System . "
        "Hak Cipta Terpelihara / All Rights Reserved"
    ),
}


# =====================================================
# SAFE TEXT HELPERS
# =====================================================

def safe_text(value, fallback="-"):
    """
    Convert a value into display-safe text.
    """

    if value is None:
        return fallback

    value = str(value).strip()
    return value if value else fallback


def safe_date(value):
    """
    Format a date value safely.
    """

    if value is None:
        return "-"

    try:
        return value.strftime("%d/%m/%Y")
    except (AttributeError, ValueError):
        return safe_text(value)


def safe_time(value):
    """
    Format a time value safely.
    """

    if value is None:
        return "-"

    try:
        return value.strftime("%I:%M %p")
    except (AttributeError, ValueError):
        return safe_text(value)


def safe_amount(value):
    """
    Convert an amount into a two-decimal float safely.
    """

    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


# =====================================================
# SINGLE COMPOUND RECEIPT PDF
# FPDF 1.x SAFE
# =====================================================

def generate_single_compound_pdf(compound):
    """
    Generate and upload a bilingual single-compound PDF receipt.

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

    # ================= LOGO =================

    logo_bottom = 20

    if os.path.exists(LOGO_PATH):
        try:
            logo_x = 70
            logo_y = 10
            logo_width = 70

            pdf.image(
                LOGO_PATH,
                x=logo_x,
                y=logo_y,
                w=logo_width,
            )

            logo_bottom = 60

        except Exception as error:
            print(f"[WARN] Failed to draw FPDF logo: {error}")

    # ================= TITLE =================

    title_y = logo_bottom + 10

    pdf.set_xy(10, title_y)
    pdf.set_font("Arial", "B", 17)
    pdf.set_text_color(30, 58, 138)

    pdf.cell(
        190,
        12,
        LABELS["single_title"],
        align="C",
    )

    # Divider line
    pdf.set_draw_color(200, 200, 200)

    pdf.line(
        20,
        title_y + 16,
        190,
        title_y + 16,
    )

    # ================= DETAILS BOX =================

    box_x = 15
    box_y = title_y + 24
    box_w = 180
    box_h = 122
    padding = 8
    inner_w = box_w - (padding * 2)

    pdf.set_fill_color(245, 247, 255)

    pdf.rect(
        box_x,
        box_y,
        box_w,
        box_h,
        style="F",
    )

    # Details heading
    y = box_y + padding

    pdf.set_xy(box_x + padding, y)
    pdf.set_font("Arial", "B", 13)
    pdf.set_text_color(0, 0, 0)

    pdf.cell(
        inner_w,
        8,
        LABELS["single_details"],
        ln=True,
    )

    y += 13

    # Detail rows
    detail_rows = [
        (LABELS["name"], compound_name),
        (LABELS["compound_no"], compound_no),
        (LABELS["plate_no"], compound_plate),
        (LABELS["date"], compound_date),
        (LABELS["time"], compound_time),
    ]

    pdf.set_font("Arial", "", 11)

    label_width = 62
    value_width = inner_w - label_width

    for label, value in detail_rows:
        pdf.set_xy(box_x + padding, y)
        pdf.set_font("Arial", "B", 10.5)

        pdf.cell(
            label_width,
            7,
            f"{label}:",
        )

        pdf.set_font("Arial", "", 10.5)

        pdf.cell(
            value_width,
            7,
            value,
            ln=True,
        )

        y += 9

    # ================= OFFENSE =================

    pdf.set_xy(box_x + padding, y)
    pdf.set_font("Arial", "B", 10.5)

    pdf.cell(
        label_width,
        7,
        f"{LABELS['offense']}:",
    )

    pdf.set_xy(
        box_x + padding + label_width,
        y,
    )

    pdf.set_font("Arial", "", 10.5)

    pdf.multi_cell(
        value_width,
        6,
        compound_offense,
    )

    # ================= AMOUNT BOX =================

    amount_y = box_y + box_h + 10
    amount_h = 18

    pdf.set_fill_color(230, 240, 255)

    pdf.rect(
        box_x,
        amount_y,
        box_w,
        amount_h,
        style="F",
    )

    pdf.set_xy(
        box_x,
        amount_y + 3,
    )

    pdf.set_font("Arial", "B", 15)
    pdf.set_text_color(0, 80, 180)

    pdf.cell(
        box_w,
        10,
        f"{LABELS['amount']}: RM {compound_amount:.2f}",
        align="C",
    )

    # ================= THANK YOU =================

    pdf.set_text_color(0, 128, 60)
    pdf.set_font("Arial", "B", 11)

    pdf.set_xy(
        10,
        amount_y + amount_h + 8,
    )

    pdf.cell(
        190,
        7,
        LABELS["thank_you_ms"],
        align="C",
    )

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "I", 10)

    pdf.set_xy(
        10,
        amount_y + amount_h + 15,
    )

    pdf.cell(
        190,
        7,
        LABELS["thank_you_en"],
        align="C",
    )

    # ================= FOOTER =================

    pdf.set_xy(
        10,
        amount_y + amount_h + 28,
    )

    pdf.set_font("Arial", "I", 9)
    pdf.set_text_color(140, 140, 140)

    pdf.cell(
        190,
        8,
        LABELS["footer"],
        align="C",
    )

    # ================= OUTPUT =================

    pdf_bytes = pdf.output(dest="S").encode("latin1")

    filename = f"compound_{compound_no}.pdf"

    return upload_to_blob(
        filename,
        pdf_bytes,
        "application/pdf",
    )


# =====================================================
# REPORTLAB MULTI-PAGE HELPERS
# =====================================================

def draw_multi_compound_header(pdf, width, height):
    """
    Draw the logo and bilingual title.

    Returns:
        float: Starting Y position for the table.
    """

    top_y = height - 70

    if LOGO_RL:
        image_width, image_height = LOGO_RL.getSize()

        logo_width = 105
        logo_height = (
            image_height / image_width
        ) * logo_width

        logo_x = (
            width - logo_width
        ) / 2

        logo_y = top_y - logo_height

        pdf.drawImage(
            LOGO_RL,
            logo_x,
            logo_y,
            width=logo_width,
            height=logo_height,
            preserveAspectRatio=True,
            mask="auto",
        )

        top_y = logo_y - 32

    pdf.setFillColor(
        colors.HexColor("#1E3A8A")
    )

    pdf.setFont(
        "Helvetica-Bold",
        17,
    )

    pdf.drawCentredString(
        width / 2,
        top_y,
        LABELS["multi_title"],
    )

    pdf.setFont(
        "Helvetica",
        11,
    )

    pdf.setFillColor(
        colors.HexColor("#6B7280")
    )

    pdf.drawCentredString(
        width / 2,
        top_y - 19,
        LABELS["subtitle"],
    )

    divider_y = top_y - 34

    pdf.setStrokeColor(
        colors.HexColor("#D1D5DB")
    )

    pdf.line(
        40,
        divider_y,
        width - 40,
        divider_y,
    )

    return divider_y - 32


def draw_multi_compound_table_header(pdf, y):
    """
    Draw the bilingual table header.

    Returns:
        float: Y position for the first data row.
    """

    table_x = 40
    table_width = 520
    header_height = 40

    pdf.setFillColor(
        colors.HexColor("#E9F0FF")
    )

    pdf.setStrokeColor(
        colors.HexColor("#BFDBFE")
    )

    pdf.roundRect(
        table_x,
        y - header_height,
        table_width,
        header_height,
        radius=5,
        fill=True,
        stroke=True,
    )

    pdf.setFillColor(colors.black)

    # Bahasa Melayu
    pdf.setFont(
        "Helvetica-Bold",
        9,
    )

    pdf.drawString(
        50,
        y - 15,
        LABELS["column_compound_no_ms"],
    )

    pdf.drawRightString(
        545,
        y - 15,
        LABELS["column_amount_ms"],
    )

    # English
    pdf.setFont(
        "Helvetica",
        8.5,
    )

    pdf.drawString(
        50,
        y - 29,
        LABELS["column_compound_no_en"],
    )

    pdf.drawRightString(
        545,
        y - 29,
        LABELS["column_amount_en"],
    )

    return y - header_height - 5


def draw_multi_compound_footer(pdf, width):
    """
    Draw the bilingual page footer.
    """

    pdf.setStrokeColor(
        colors.HexColor("#E5E7EB")
    )

    pdf.line(
        40,
        48,
        width - 40,
        48,
    )

    pdf.setFont(
        "Helvetica",
        8.5,
    )

    pdf.setFillColor(
        colors.HexColor("#6B7280")
    )

    pdf.drawCentredString(
        width / 2,
        30,
        LABELS["footer"],
    )


# =====================================================
# MULTIPLE COMPOUND RECEIPT PDF
# REPORTLAB
# =====================================================

def generate_multi_compound_pdf(compounds, total_amount):
    """
    Generate a bilingual multiple-compound PDF receipt.

    Args:
        compounds:
            List of compound dictionaries.

            Expected keys:
                compoundnum
                amount

        total_amount:
            Total paid amount.

    Returns:
        BytesIO: PDF buffer.
    """

    buffer = BytesIO()

    pdf = canvas.Canvas(
        buffer,
        pagesize=A4,
    )

    width, height = A4

    safe_total = safe_amount(total_amount)

    # First page header
    y = draw_multi_compound_header(
        pdf,
        width,
        height,
    )

    y = draw_multi_compound_table_header(
        pdf,
        y,
    )

    row_height = 27

    # ================= TABLE ROWS =================

    for index, compound in enumerate(compounds):

        if y <= 105:
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
            colors.HexColor("#F9FAFB")
            if index % 2 == 0
            else colors.white
        )

        pdf.setFillColor(
            row_background
        )

        pdf.setStrokeColor(
            colors.HexColor("#E5E7EB")
        )

        pdf.rect(
            40,
            y - row_height,
            520,
            row_height,
            fill=True,
            stroke=True,
        )

        pdf.setFillColor(
            colors.HexColor("#111827")
        )

        pdf.setFont(
            "Helvetica",
            10,
        )

        pdf.drawString(
            50,
            y - 18,
            compound_number,
        )

        pdf.drawRightString(
            545,
            y - 18,
            f"{amount:.2f}",
        )

        y -= row_height

    # ================= TOTAL =================

    if y <= 120:
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

    total_box_height = 40

    pdf.setFillColor(
        colors.HexColor("#D6E9FF")
    )

    pdf.setStrokeColor(
        colors.HexColor("#93C5FD")
    )

    pdf.roundRect(
        40,
        y - total_box_height - 10,
        520,
        total_box_height,
        radius=6,
        fill=True,
        stroke=True,
    )

    pdf.setFillColor(
        colors.HexColor("#111827")
    )

    pdf.setFont(
        "Helvetica-Bold",
        11,
    )

    pdf.drawString(
        50,
        y - 36,
        LABELS["total"],
    )

    pdf.setFillColor(
        colors.HexColor("#1D4ED8")
    )

    pdf.setFont(
        "Helvetica-Bold",
        14,
    )

    pdf.drawRightString(
        545,
        y - 36,
        f"RM {safe_total:.2f}",
    )

    # ================= THANK YOU =================

    thank_you_y = y - 92

    pdf.setFillColor(
        colors.HexColor("#15803D")
    )

    pdf.setFont(
        "Helvetica-Bold",
        11,
    )

    pdf.drawCentredString(
        width / 2,
        thank_you_y,
        LABELS["thank_you_ms"],
    )

    pdf.setFont(
        "Helvetica",
        10,
    )

    pdf.drawCentredString(
        width / 2,
        thank_you_y - 16,
        LABELS["thank_you_en"],
    )

    # ================= FOOTER =================

    draw_multi_compound_footer(
        pdf,
        width,
    )

    pdf.save()

    buffer.seek(0)

    return buffer