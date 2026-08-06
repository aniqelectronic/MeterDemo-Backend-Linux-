from io import BytesIO
import datetime
import html
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# =========================================================
# LOGO PRELOAD
# =========================================================

COMPANY_LOGO = None
COMPANY_LOGO_PATH = "app/resources/images/jip_logo.png"


def _load_logo(path, label):
    if not os.path.exists(path):
        print(f"[WARN] {label} logo not found at: {path}")
        return None

    try:
        with open(path, "rb") as logo_file:
            image = ImageReader(BytesIO(logo_file.read()))

        print(f"[INFO] {label} logo preloaded successfully.")
        return image
    except Exception as error:
        print(f"[WARN] Failed to load {label} logo: {error}")
        return None


COMPANY_LOGO = _load_logo(COMPANY_LOGO_PATH, "Company")


# =========================================================
# HELPERS
# =========================================================

def _safe_text(value, fallback="-"):
    if value is None:
        return fallback

    clean_value = str(value).strip()

    if not clean_value or clean_value.lower() == "null":
        return fallback

    return clean_value


def _safe_html(value, fallback="-"):
    return html.escape(_safe_text(value, fallback))


def _safe_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _format_money(value):
    return f"{_safe_float(value):,.2f}"


def _format_paid_datetime(value):
    if isinstance(value, datetime.datetime):
        paid_date = value
    elif isinstance(value, datetime.date):
        paid_date = datetime.datetime.combine(
            value,
            datetime.time.min,
        )
    else:
        try:
            paid_date = datetime.datetime.fromisoformat(str(value))
        except (TypeError, ValueError):
            return _safe_text(value)

    return paid_date.strftime("%d %b %Y %I:%M %p")


def _bilingual_paragraph(
    malay,
    english,
    malay_size=8.5,
    english_size=7,
    malay_color="#111827",
    english_color="#6B7280",
    alignment=TA_LEFT,
    leading=10,
):
    style = ParagraphStyle(
        name=f"Bilingual-{id(malay)}-{id(english)}",
        fontName="Helvetica",
        fontSize=malay_size,
        leading=leading,
        alignment=alignment,
        textColor=colors.HexColor(malay_color),
        spaceBefore=0,
        spaceAfter=0,
        allowWidows=0,
        allowOrphans=0,
    )

    content = (
        f'<font name="Helvetica-Bold" size="{malay_size}" '
        f'color="{malay_color}">{_safe_html(malay)}</font>'
        f'<br/>'
        f'<font name="Helvetica-Oblique" size="{english_size}" '
        f'color="{english_color}">{_safe_html(english)}</font>'
    )

    return Paragraph(content, style)


def _value_paragraph(
    value,
    font_size=8.5,
    color="#111827",
    alignment=TA_LEFT,
    leading=10,
    bold=False,
):
    font_name = "Helvetica-Bold" if bold else "Helvetica"

    style = ParagraphStyle(
        name=f"Value-{id(value)}",
        fontName=font_name,
        fontSize=font_size,
        leading=leading,
        alignment=alignment,
        textColor=colors.HexColor(color),
        spaceBefore=0,
        spaceAfter=0,
        allowWidows=0,
        allowOrphans=0,
        wordWrap="LTR",
    )

    return Paragraph(_safe_html(value), style)


# =========================================================
# PAGE HEADER AND FOOTER
# =========================================================

def _draw_page_template(canvas_obj, document):
    canvas_obj.saveState()

    width, height = A4

    primary_blue = colors.HexColor("#123B70")
    secondary_blue = colors.HexColor("#1976D2")
    accent_blue = colors.HexColor("#42A5F5")
    grey_text = colors.HexColor("#666666")

    header_height = 44 * mm

    canvas_obj.setFillColor(primary_blue)
    canvas_obj.rect(
        0,
        height - header_height,
        width,
        header_height,
        fill=1,
        stroke=0,
    )

    canvas_obj.setFillColor(secondary_blue)
    canvas_obj.rect(
        0,
        height - 11 * mm,
        width,
        11 * mm,
        fill=1,
        stroke=0,
    )

    canvas_obj.setFillColor(accent_blue)
    canvas_obj.rect(
        0,
        height - 3 * mm,
        width,
        3 * mm,
        fill=1,
        stroke=0,
    )

    canvas_obj.setFillColor(colors.HexColor("#0B2B52"))
    canvas_obj.rect(
        0,
        height - header_height,
        width,
        10 * mm,
        fill=1,
        stroke=0,
    )


    if COMPANY_LOGO:
        try:
            canvas_obj.drawImage(
                COMPANY_LOGO,
                width - 40 * mm,
                height - 31 * mm,
                width=29 * mm,
                height=18 * mm,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception as error:
            print(f"[WARN] Failed to draw company logo: {error}")

    canvas_obj.setFillColor(colors.white)
    canvas_obj.setFont("Helvetica-Bold", 14)
    canvas_obj.drawCentredString(
        width / 2,
        height - 16 * mm,
        "TIP DIGITAL KIOSK",
    )

    canvas_obj.setFont("Helvetica-Oblique", 8)
    canvas_obj.drawCentredString(
        width / 2,
        height - 21 * mm,
        "DIGITAL SELF-SERVICE KIOSK",
    )

    canvas_obj.setFont("Helvetica-Bold", 8.5)
    canvas_obj.drawCentredString(
        width / 2,
        height - 31 * mm,
        "RESIT BAYARAN BIL",
    )

    canvas_obj.setFont("Helvetica-Oblique", 7)
    canvas_obj.drawCentredString(
        width / 2,
        height - 35 * mm,
        "BILL PAYMENT RECEIPT",
    )

    canvas_obj.setFont("Helvetica-Bold", 6.5)
    canvas_obj.drawCentredString(
        width / 2,
        height - 39 * mm,
        "Dijana oleh TIP",
    )

    canvas_obj.setFont("Helvetica-Oblique", 5.8)
    canvas_obj.drawCentredString(
        width / 2,
        height - 42 * mm,
        "Generated by TIP",
    )

    canvas_obj.setStrokeColor(colors.HexColor("#D9E8FF"))
    canvas_obj.line(
        15 * mm,
        20 * mm,
        width - 15 * mm,
        20 * mm,
    )

    if COMPANY_LOGO:
        try:
            canvas_obj.drawImage(
                COMPANY_LOGO,
                width - 33 * mm,
                7 * mm,
                width=17 * mm,
                height=10 * mm,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception:
            pass

    canvas_obj.setFillColor(primary_blue)
    canvas_obj.setFont("Helvetica-Bold", 7)
    canvas_obj.drawCentredString(
        width / 2,
        15.5 * mm,
        "TIP Digital Kiosk",
    )

    canvas_obj.setFillColor(grey_text)
    canvas_obj.setFont("Helvetica-Oblique", 6)
    canvas_obj.drawCentredString(
        width / 2,
        12.5 * mm,
        "Digital Self-Service Kiosk",
    )

    canvas_obj.setFont("Helvetica", 5.8)
    canvas_obj.drawCentredString(
        width / 2,
        9.5 * mm,
        "Resit ini dijana secara elektronik dan tidak memerlukan tandatangan.",
    )

    canvas_obj.setFont("Helvetica-Oblique", 5.4)
    canvas_obj.drawCentredString(
        width / 2,
        6.7 * mm,
        "This receipt is electronically generated and requires no signature.",
    )

    canvas_obj.setFont("Helvetica", 5.5)
    canvas_obj.drawRightString(
        width - 15 * mm,
        4.2 * mm,
        f"Halaman / Page {document.page}",
    )

    canvas_obj.restoreState()


# =========================================================
# RECEIPT SECTIONS
# =========================================================

def _build_receipt_info(
    paid_date,
    payment_method,
    order_no,
    bank_trx_no,
):
    title = _bilingual_paragraph(
        "Resit Bayaran Bil",
        "Bill Payment Receipt",
        malay_size=17,
        english_size=10,
        malay_color="#123B70",
        english_color="#1976D2",
        leading=14,
    )

    order_paragraph = _value_paragraph(
        f"#{_safe_text(order_no)}",
        font_size=9,
        color="#1976D2",
        bold=True,
    )

    left_block = Table(
        [[title], [order_paragraph]],
        colWidths=[70 * mm],
    )

    left_block.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )

    metadata_rows = [
        [
            _bilingual_paragraph(
                "Tarikh Dibayar",
                "Paid Date",
                malay_size=7.5,
                english_size=6.5,
                leading=8,
            ),
            _value_paragraph(
                _format_paid_datetime(paid_date),
                font_size=7.5,
                leading=9,
            ),
        ],
        [
            _bilingual_paragraph(
                "Kaedah Pembayaran",
                "Payment Method",
                malay_size=7.5,
                english_size=6.5,
                leading=8,
            ),
            _value_paragraph(
                _safe_text(payment_method),
                font_size=7.5,
                leading=9,
            ),
        ],
    ]

    if _safe_text(bank_trx_no) != "-":
        metadata_rows.append(
            [
                _bilingual_paragraph(
                    "No. Transaksi Bank",
                    "Bank Transaction No.",
                    malay_size=7.5,
                    english_size=6.5,
                    leading=8,
                ),
                _value_paragraph(
                    _safe_text(bank_trx_no),
                    font_size=7.5,
                    leading=9,
                ),
            ]
        )

    metadata_table = Table(
        metadata_rows,
        colWidths=[43 * mm, 62 * mm],
        hAlign="RIGHT",
    )

    metadata_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    info_table = Table(
        [[left_block, metadata_table]],
        colWidths=[70 * mm, 110 * mm],
    )

    info_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    return info_table


def _build_bill_details(
    bill_type,
    bill_code,
    account_number,
    bill_amount,
    total_amount,
):
    rows = [
        [
            _bilingual_paragraph(
                "Jenis / Penyedia Bil",
                "Bill Type / Provider",
                malay_size=8,
                english_size=6.8,
                leading=9,
            ),
            _value_paragraph(
                _safe_text(bill_type),
                font_size=9,
                leading=11,
                bold=True,
            ),
        ],
        [
            _bilingual_paragraph(
                "Kod Bil",
                "Bill Code",
                malay_size=8,
                english_size=6.8,
                leading=9,
            ),
            _value_paragraph(
                _safe_text(bill_code),
                font_size=9,
                leading=11,
                bold=True,
            ),
        ],
        [
            _bilingual_paragraph(
                "Nombor Akaun",
                "Account Number",
                malay_size=8,
                english_size=6.8,
                leading=9,
            ),
            _value_paragraph(
                _safe_text(account_number),
                font_size=9,
                leading=11,
                bold=True,
            ),
        ],
        [
            _bilingual_paragraph(
                "Amaun Bil",
                "Bill Amount",
                malay_size=8,
                english_size=6.8,
                leading=9,
            ),
            _value_paragraph(
                f"RM {_format_money(bill_amount)}",
                font_size=9,
                leading=11,
                bold=True,
            ),
        ],
    ]

    details_table = Table(
        rows,
        colWidths=[57 * mm, 123 * mm],
        hAlign="LEFT",
    )

    style_commands = [
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#C9DDF2")),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#DCE9F6")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]

    for row_index in range(len(rows)):
        background = (
            colors.HexColor("#F5F9FE")
            if row_index % 2 == 0
            else colors.white
        )
        style_commands.append(
            ("BACKGROUND", (0, row_index), (-1, row_index), background)
        )

    details_table.setStyle(TableStyle(style_commands))

    total_table = Table(
        [
            [
                _bilingual_paragraph(
                    "Jumlah Dibayar",
                    "Total Paid",
                    malay_size=11,
                    english_size=8,
                    malay_color="#FFFFFF",
                    english_color="#DCEBFF",
                    leading=12,
                ),
                _value_paragraph(
                    f"RM {_format_money(total_amount)}",
                    font_size=16,
                    color="#FFFFFF",
                    alignment=TA_RIGHT,
                    bold=True,
                ),
            ]
        ],
        colWidths=[115 * mm, 65 * mm],
    )

    total_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#123B70")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )

    note_style = ParagraphStyle(
        name="BillReceiptNote",
        fontName="Helvetica",
        fontSize=7,
        leading=9.5,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#5F6B78"),
        spaceBefore=0,
        spaceAfter=0,
    )

    note = Paragraph(
        (
            '<font name="Helvetica-Bold">'
            "Simpan resit ini sebagai bukti pembayaran. "
            "Kemas kini akaun bil tertakluk kepada tempoh pemprosesan penyedia bil."
            "</font>"
            "<br/>"
            '<font name="Helvetica-Oblique">'
            "Please retain this receipt as proof of payment. "
            "Bill account updates are subject to the provider's processing time."
            "</font>"
        ),
        note_style,
    )

    return [
        details_table,
        Spacer(1, 7 * mm),
        total_table,
        Spacer(1, 6 * mm),
        note,
    ]


# =========================================================
# BILL RECEIPT GENERATOR
# =========================================================

def generate_bill_receipt(
    paid_date: datetime.datetime,
    payment_method: str,
    bill_type: str,
    bill_code: str,
    account_number: str,
    bill_amount: float,
    total_amount: float,
    order_no: str = None,
    bank_trx_no: str = None,
):
    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=50 * mm,
        bottomMargin=24 * mm,
        title="Resit Bayaran Bil / Bill Payment Receipt",
        author="TIP",
    )

    story = [
        _build_receipt_info(
            paid_date=paid_date,
            payment_method=payment_method,
            order_no=order_no,
            bank_trx_no=bank_trx_no,
        ),
        Spacer(1, 8 * mm),
        _bilingual_paragraph(
            "Butiran Pembayaran Bil",
            "Bill Payment Details",
            malay_size=11,
            english_size=8,
            malay_color="#123B70",
            english_color="#1976D2",
            leading=12,
        ),
        Spacer(1, 4 * mm),
    ]

    story.extend(
        _build_bill_details(
            bill_type=bill_type,
            bill_code=bill_code,
            account_number=account_number,
            bill_amount=bill_amount,
            total_amount=total_amount,
        )
    )

    document.build(
        story,
        onFirstPage=_draw_page_template,
        onLaterPages=_draw_page_template,
    )

    buffer.seek(0)
    return buffer.read()


# =========================================================
# LOCAL TEST
# Remove this block when not needed.
# =========================================================

if __name__ == "__main__":
    pdf_bytes = generate_bill_receipt(
        paid_date=datetime.datetime.now(),
        payment_method="DuitNow QR",
        bill_type="Tenaga Nasional Berhad",
        bill_code="TNB",
        account_number="220411163904",
        bill_amount=6.00,
        total_amount=6.00,
        order_no="ORD-BILL-20260805-0001",
        bank_trx_no="BANK-QR-987654321",
    )

    with open("/mnt/data/sample_bill_receipt_generic.pdf", "wb") as output_file:
        output_file.write(pdf_bytes)

    print("PDF generated: /mnt/data/sample_bill_receipt.pdf")