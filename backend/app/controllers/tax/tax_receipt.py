from io import BytesIO
import html
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# =========================================================
# LOGO HANDLING
# =========================================================

LOGO_PATH = "app/resources/images/jip_logo.png"
LOGO_RL = None

if os.path.exists(LOGO_PATH):
    try:
        with open(LOGO_PATH, "rb") as logo_file:
            LOGO_RL = ImageReader(
                BytesIO(logo_file.read())
            )

        print(
            "[INFO] Logo loaded for "
            "ReportLab multiple-tax PDF"
        )

    except Exception as error:
        print(
            "[WARN] Failed to load ReportLab logo: "
            f"{error}"
        )

else:
    print(
        "[WARN] Logo path does not exist: "
        f"{LOGO_PATH}"
    )


# =========================================================
# HELPERS
# =========================================================

def _safe_text(value, fallback="-"):
    """
    Return escaped display text.
    """
    if value is None:
        return fallback

    text = str(value).strip()

    if not text:
        return fallback

    return html.escape(text)


def _safe_amount(value):
    """
    Return a valid numeric amount.
    """
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _format_money(value):
    """
    Format amount with comma separators and two decimals.
    """
    return f"{_safe_amount(value):,.2f}"


def _format_date(value):
    """
    Format date values when possible.
    """
    if not value:
        return "-"

    try:
        return value.strftime("%d/%m/%Y")
    except (AttributeError, ValueError):
        return _safe_text(value)


def _build_address(tax):
    """
    Combine all available address fields.
    """
    address_parts = [
        tax.get("lot_no"),
        tax.get("house_no"),
        tax.get("street"),
        tax.get("address1"),
        tax.get("address2"),
        tax.get("zone"),
    ]

    cleaned_parts = []

    for part in address_parts:
        if part is None:
            continue

        text = str(part).strip()

        if text:
            cleaned_parts.append(text)

    if not cleaned_parts:
        return "-"

    return ", ".join(cleaned_parts)


def _bilingual_text(
    malay,
    english,
    malay_size=9,
    english_size=7.5,
    malay_color="#111827",
    english_color="#6B7280",
    alignment=TA_LEFT,
    leading=11,
):
    """
    Create Malay bold text with italic English underneath.
    """
    style = ParagraphStyle(
        name=f"Bilingual-{id(malay)}-{id(english)}",
        fontName="Helvetica",
        fontSize=malay_size,
        leading=leading,
        textColor=colors.HexColor(malay_color),
        alignment=alignment,
        spaceAfter=0,
        spaceBefore=0,
        allowWidows=0,
        allowOrphans=0,
    )

    content = (
        f'<font name="Helvetica-Bold" size="{malay_size}" '
        f'color="{malay_color}">{_safe_text(malay)}</font>'
        f'<br/>'
        f'<font name="Helvetica-Oblique" size="{english_size}" '
        f'color="{english_color}">{_safe_text(english)}</font>'
    )

    return Paragraph(
        content,
        style,
    )


def _normal_paragraph(
    text,
    font_size=8.5,
    color="#111827",
    alignment=TA_LEFT,
    leading=11,
    bold=False,
):
    """
    Create wrapped normal text.
    """
    font_name = (
        "Helvetica-Bold"
        if bold
        else "Helvetica"
    )

    style = ParagraphStyle(
        name=f"Normal-{id(text)}",
        fontName=font_name,
        fontSize=font_size,
        leading=leading,
        textColor=colors.HexColor(color),
        alignment=alignment,
        spaceAfter=0,
        spaceBefore=0,
        allowWidows=0,
        allowOrphans=0,
        wordWrap="LTR",
    )

    return Paragraph(
        _safe_text(text),
        style,
    )


# =========================================================
# PAGE HEADER AND FOOTER
# =========================================================

def _draw_page_background(canvas_obj, document):
    """
    Draw the blue receipt header and footer on every page.
    """
    canvas_obj.saveState()

    page_width, page_height = A4

    primary_blue = colors.HexColor("#003B8E")
    secondary_blue = colors.HexColor("#0A66D8")
    light_blue = colors.HexColor("#1C8CFF")
    grey_text = colors.HexColor("#6B7280")

    header_height = 44 * mm

    # Main header
    canvas_obj.setFillColor(primary_blue)
    canvas_obj.rect(
        0,
        page_height - header_height,
        page_width,
        header_height,
        fill=1,
        stroke=0,
    )

    # Accent strips
    canvas_obj.setFillColor(secondary_blue)
    canvas_obj.rect(
        0,
        page_height - 11 * mm,
        page_width,
        11 * mm,
        fill=1,
        stroke=0,
    )

    canvas_obj.setFillColor(light_blue)
    canvas_obj.rect(
        0,
        page_height - 3 * mm,
        page_width,
        3 * mm,
        fill=1,
        stroke=0,
    )

    # Decorative circle
    canvas_obj.setFillColor(
        colors.Color(
            1,
            1,
            1,
            alpha=0.07,
        )
    )
    canvas_obj.circle(
        page_width - 10 * mm,
        page_height - 12 * mm,
        27 * mm,
        fill=1,
        stroke=0,
    )

    # Logo
    if LOGO_RL:
        try:
            image_width, image_height = LOGO_RL.getSize()

            max_width = 29 * mm
            max_height = 20 * mm

            ratio = min(
                max_width / image_width,
                max_height / image_height,
            )

            draw_width = image_width * ratio
            draw_height = image_height * ratio

            canvas_obj.drawImage(
                LOGO_RL,
                13 * mm,
                page_height - 35 * mm,
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

    # Header title
    canvas_obj.setFillColor(colors.white)
    canvas_obj.setFont(
        "Helvetica-Bold",
        15,
    )
    canvas_obj.drawCentredString(
        page_width / 2,
        page_height - 17 * mm,
        "RESIT PELBAGAI CUKAI",
    )

    canvas_obj.setFont(
        "Helvetica-Oblique",
        9,
    )
    canvas_obj.drawCentredString(
        page_width / 2,
        page_height - 23 * mm,
        "MULTIPLE TAX RECEIPT",
    )

    canvas_obj.setFont(
        "Helvetica-Bold",
        8,
    )
    canvas_obj.drawCentredString(
        page_width / 2,
        page_height - 31 * mm,
        "Rekod Transaksi Rasmi",
    )

    canvas_obj.setFont(
        "Helvetica-Oblique",
        7,
    )
    canvas_obj.drawCentredString(
        page_width / 2,
        page_height - 35.5 * mm,
        "Official Transaction Record",
    )

    # Footer line
    canvas_obj.setStrokeColor(
        colors.HexColor("#DCE8F8")
    )
    canvas_obj.line(
        15 * mm,
        18 * mm,
        page_width - 15 * mm,
        18 * mm,
    )

    # Footer
    canvas_obj.setFillColor(primary_blue)
    canvas_obj.setFont(
        "Helvetica-Bold",
        7.5,
    )
    canvas_obj.drawCentredString(
        page_width / 2,
        12.5 * mm,
        "2026 Juara Inovasi Pintar System - Hak Cipta Terpelihara",
    )

    canvas_obj.setFillColor(grey_text)
    canvas_obj.setFont(
        "Helvetica-Oblique",
        6.5,
    )
    canvas_obj.drawCentredString(
        page_width / 2,
        8.5 * mm,
        "All Rights Reserved",
    )

    # Page number
    canvas_obj.setFont(
        "Helvetica",
        6.5,
    )
    canvas_obj.drawRightString(
        page_width - 15 * mm,
        8.5 * mm,
        f"Halaman / Page {document.page}",
    )

    canvas_obj.restoreState()


# =========================================================
# MULTIPLE TAX RECEIPT PDF
# =========================================================

def generate_multi_tax_pdf(Taxes, total_amount):
    """
    Generate a responsive bilingual multiple-tax receipt.

    Improvements:
    - Malay labels are bold.
    - English labels are italic underneath.
    - Long bill numbers, property types and addresses wrap automatically.
    - A complete row moves to the next page when it cannot fit.
    - Table headers repeat on every page.
    - Total and thank-you blocks stay together.
    - Page header and footer repeat on every page.

    Args:
        Taxes:
            List of tax dictionaries.

        total_amount:
            Overall paid amount.

    Returns:
        BytesIO containing the generated PDF.
    """

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=51 * mm,
        bottomMargin=23 * mm,
        title=(
            "Resit Pelbagai Cukai / "
            "Multiple Tax Receipt"
        ),
        author="Juara Inovasi Pintar System",
    )

    story = []

    # =====================================================
    # TABLE DATA
    # =====================================================

    header_row = [
        _bilingual_text(
            "No. Bil",
            "Bill No.",
            malay_size=8,
            english_size=6.8,
            malay_color="#FFFFFF",
            english_color="#DCEBFF",
            alignment=TA_LEFT,
            leading=9,
        ),
        _bilingual_text(
            "Jenis Harta",
            "Property Type",
            malay_size=8,
            english_size=6.8,
            malay_color="#FFFFFF",
            english_color="#DCEBFF",
            alignment=TA_LEFT,
            leading=9,
        ),
        _bilingual_text(
            "Alamat",
            "Address",
            malay_size=8,
            english_size=6.8,
            malay_color="#FFFFFF",
            english_color="#DCEBFF",
            alignment=TA_LEFT,
            leading=9,
        ),
        _bilingual_text(
            "Jumlah (RM)",
            "Amount (RM)",
            malay_size=8,
            english_size=6.8,
            malay_color="#FFFFFF",
            english_color="#DCEBFF",
            alignment=TA_RIGHT,
            leading=9,
        ),
    ]

    table_data = [header_row]

    for tax in Taxes:
        bill_number = tax.get(
            "bill_no",
            "-",
        )

        property_type = tax.get(
            "property_type",
            "-",
        )

        full_address = _build_address(
            tax
        )

        amount = _safe_amount(
            tax.get("amount")
        )

        table_data.append(
            [
                _normal_paragraph(
                    bill_number,
                    font_size=8,
                    leading=10,
                    bold=True,
                ),
                _normal_paragraph(
                    property_type,
                    font_size=8,
                    leading=10,
                ),
                _normal_paragraph(
                    full_address,
                    font_size=8,
                    leading=10,
                ),
                _normal_paragraph(
                    _format_money(amount),
                    font_size=8.5,
                    color="#003B8E",
                    alignment=TA_RIGHT,
                    leading=10,
                    bold=True,
                ),
            ]
        )

    # Column widths fit within A4 content width.
    column_widths = [
        34 * mm,
        35 * mm,
        83 * mm,
        28 * mm,
    ]

    tax_table = Table(
        table_data,
        colWidths=column_widths,
        repeatRows=1,
        hAlign="LEFT",
        splitByRow=1,
        spaceBefore=0,
        spaceAfter=0,
    )

    table_style_commands = [
        # Header
        (
            "BACKGROUND",
            (0, 0),
            (-1, 0),
            colors.HexColor("#0A66D8"),
        ),
        (
            "VALIGN",
            (0, 0),
            (-1, -1),
            "TOP",
        ),
        (
            "LEFTPADDING",
            (0, 0),
            (-1, -1),
            8,
        ),
        (
            "RIGHTPADDING",
            (0, 0),
            (-1, -1),
            8,
        ),
        (
            "TOPPADDING",
            (0, 0),
            (-1, 0),
            9,
        ),
        (
            "BOTTOMPADDING",
            (0, 0),
            (-1, 0),
            9,
        ),
        # Body rows
        (
            "TOPPADDING",
            (0, 1),
            (-1, -1),
            10,
        ),
        (
            "BOTTOMPADDING",
            (0, 1),
            (-1, -1),
            10,
        ),
        (
            "GRID",
            (0, 0),
            (-1, -1),
            0.5,
            colors.HexColor("#DCE8F8"),
        ),
        (
            "LINEBELOW",
            (0, 0),
            (-1, 0),
            1,
            colors.HexColor("#004AAE"),
        ),
    ]

    # Alternate row backgrounds.
    for row_index in range(
        1,
        len(table_data),
    ):
        background = (
            colors.HexColor("#F4F8FF")
            if row_index % 2 == 0
            else colors.white
        )

        table_style_commands.append(
            (
                "BACKGROUND",
                (0, row_index),
                (-1, row_index),
                background,
            )
        )

    tax_table.setStyle(
        TableStyle(
            table_style_commands
        )
    )

    story.append(tax_table)
    story.append(Spacer(1, 8 * mm))

    # =====================================================
    # TOTAL AND THANK-YOU BLOCK
    # =====================================================

    total_label = _bilingual_text(
        "Jumlah Keseluruhan",
        "Total Amount",
        malay_size=11,
        english_size=8,
        malay_color="#003B8E",
        english_color="#6B7280",
        alignment=TA_LEFT,
        leading=12,
    )

    total_value = _normal_paragraph(
        f"RM {_format_money(total_amount)}",
        font_size=16,
        color="#0A66D8",
        alignment=TA_RIGHT,
        leading=18,
        bold=True,
    )

    total_table = Table(
        [
            [
                total_label,
                total_value,
            ]
        ],
        colWidths=[
            110 * mm,
            70 * mm,
        ],
        hAlign="LEFT",
    )

    total_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#EAF3FF"),
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.8,
                    colors.HexColor("#BFD7FF"),
                ),
                (
                    "LINEBEFORE",
                    (0, 0),
                    (0, 0),
                    4,
                    colors.HexColor("#0A66D8"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    12,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    12,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    11,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    11,
                ),
            ]
        )
    )

    thank_you_style = ParagraphStyle(
        name="ThankYou",
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#15803D"),
        alignment=TA_CENTER,
        spaceBefore=0,
        spaceAfter=0,
    )

    thank_you = Paragraph(
        (
            '<font name="Helvetica-Bold" size="10">'
            "Terima kasih atas pembayaran anda."
            "</font>"
            "<br/>"
            '<font name="Helvetica-Oblique" size="8">'
            "Thank you for your payment."
            "</font>"
        ),
        thank_you_style,
    )

    # Keep the total and thank-you message together.
    story.append(
        KeepTogether(
            [
                total_table,
                Spacer(1, 6 * mm),
                thank_you,
            ]
        )
    )

    # =====================================================
    # BUILD PDF
    # =====================================================

    document.build(
        story,
        onFirstPage=_draw_page_background,
        onLaterPages=_draw_page_background,
    )

    buffer.seek(0)

    return buffer