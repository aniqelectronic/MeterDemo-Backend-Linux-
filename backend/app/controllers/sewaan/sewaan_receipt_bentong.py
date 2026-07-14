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

BENTONG_LOGO = None
BENTONG_LOGO_PATH = "app/resources/images/majlisbentong.png"

COMPANY_LOGO = None
COMPANY_LOGO_PATH = "app/resources/images/jip_logo.png"


try:
    if os.path.exists(BENTONG_LOGO_PATH):
        with open(BENTONG_LOGO_PATH, "rb") as logo_file:
            BENTONG_LOGO = ImageReader(
                BytesIO(logo_file.read())
            )

        print(
            "[INFO] Bentong logo preloaded successfully."
        )
    else:
        print(
            f"[WARN] Bentong logo not found at: "
            f"{BENTONG_LOGO_PATH}"
        )

except Exception as error:
    print(
        f"[WARN] Failed to load Bentong logo: "
        f"{error}"
    )


try:
    if os.path.exists(COMPANY_LOGO_PATH):
        with open(COMPANY_LOGO_PATH, "rb") as logo_file:
            COMPANY_LOGO = ImageReader(
                BytesIO(logo_file.read())
            )

        print(
            "[INFO] Company logo preloaded successfully."
        )
    else:
        print(
            f"[WARN] Company logo not found at: "
            f"{COMPANY_LOGO_PATH}"
        )

except Exception as error:
    print(
        f"[WARN] Failed to load company logo: "
        f"{error}"
    )


# =========================================================
# HELPERS
# =========================================================

def _safe_text(value, fallback="-"):
    if value is None:
        return fallback

    text = str(value).strip()

    if not text:
        return fallback

    return text


def _safe_html(value, fallback="-"):
    return html.escape(
        _safe_text(value, fallback)
    )


def _safe_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _format_money(value):
    return f"{_safe_float(value):,.2f}"


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
        return _safe_text(value)


def _build_address(*parts):
    cleaned_parts = []

    for part in parts:
        text = str(part or "").strip()

        if text:
            cleaned_parts.append(text)

    return (
        ", ".join(cleaned_parts)
        if cleaned_parts
        else "-"
    )


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
        f'<font name="Helvetica-Bold" '
        f'size="{malay_size}" '
        f'color="{malay_color}">'
        f'{_safe_html(malay)}'
        f'</font>'
        f'<br/>'
        f'<font name="Helvetica-Oblique" '
        f'size="{english_size}" '
        f'color="{english_color}">'
        f'{_safe_html(english)}'
        f'</font>'
    )

    return Paragraph(
        content,
        style,
    )


def _value_paragraph(
    value,
    font_size=8.5,
    color="#111827",
    alignment=TA_LEFT,
    leading=10,
    bold=False,
):
    font_name = (
        "Helvetica-Bold"
        if bold
        else "Helvetica"
    )

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

    return Paragraph(
        _safe_html(value),
        style,
    )


# =========================================================
# API NORMALIZATION
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
# PAGE HEADER AND FOOTER
# =========================================================

def _draw_page_template(canvas_obj, document):
    canvas_obj.saveState()

    width, height = A4

    primary_blue = colors.HexColor("#003B8E")
    secondary_blue = colors.HexColor("#0057D9")
    light_blue = colors.HexColor("#0A84FF")
    grey_text = colors.HexColor("#666666")

    header_height = 44 * mm

    # Header background
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

    canvas_obj.setFillColor(light_blue)
    canvas_obj.rect(
        0,
        height - 3 * mm,
        width,
        3 * mm,
        fill=1,
        stroke=0,
    )

    canvas_obj.setFillColor(colors.HexColor("#002B6B"))
    canvas_obj.rect(
        0,
        height - header_height,
        width,
        10 * mm,
        fill=1,
        stroke=0,
    )

    # Logos
    if BENTONG_LOGO:
        try:
            canvas_obj.drawImage(
                BENTONG_LOGO,
                13 * mm,
                height - 34 * mm,
                width=24 * mm,
                height=24 * mm,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception as error:
            print(
                f"[WARN] Failed to draw Bentong logo: "
                f"{error}"
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
            print(
                f"[WARN] Failed to draw company logo: "
                f"{error}"
            )

    # Header text
    canvas_obj.setFillColor(colors.white)

    canvas_obj.setFont(
        "Helvetica-Bold",
        14,
    )
    canvas_obj.drawCentredString(
        width / 2,
        height - 16 * mm,
        "MAJLIS PERBANDARAN BENTONG",
    )

    canvas_obj.setFont(
        "Helvetica-Oblique",
        8,
    )
    canvas_obj.drawCentredString(
        width / 2,
        height - 21 * mm,
        "BENTONG MUNICIPAL COUNCIL",
    )

    canvas_obj.setFont(
        "Helvetica",
        6.5,
    )
    canvas_obj.drawCentredString(
        width / 2,
        height - 25 * mm,
        "Jalan Ketari, 28700 Bentong, Pahang Darul Makmur",
    )

    canvas_obj.setFont(
        "Helvetica-Bold",
        8.5,
    )
    canvas_obj.drawCentredString(
        width / 2,
        height - 31 * mm,
        "RESIT BAYARAN SEWAAN",
    )

    canvas_obj.setFont(
        "Helvetica-Oblique",
        7,
    )
    canvas_obj.drawCentredString(
        width / 2,
        height - 35 * mm,
        "RENTAL PAYMENT RECEIPT",
    )

    canvas_obj.setFont(
        "Helvetica-Bold",
        6.5,
    )
    canvas_obj.drawCentredString(
        width / 2,
        height - 39 * mm,
        "Dijana oleh TIP Bentong",
    )

    canvas_obj.setFont(
        "Helvetica-Oblique",
        5.8,
    )
    canvas_obj.drawCentredString(
        width / 2,
        height - 42 * mm,
        "Generated by TIP Bentong",
    )

    # Footer
    canvas_obj.setStrokeColor(
        colors.HexColor("#D9E8FF")
    )
    canvas_obj.line(
        15 * mm,
        20 * mm,
        width - 15 * mm,
        20 * mm,
    )

    if BENTONG_LOGO:
        try:
            canvas_obj.drawImage(
                BENTONG_LOGO,
                17 * mm,
                7 * mm,
                width=11 * mm,
                height=11 * mm,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception:
            pass

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
    canvas_obj.setFont(
        "Helvetica-Bold",
        7,
    )
    canvas_obj.drawCentredString(
        width / 2,
        15.5 * mm,
        "Majlis Perbandaran Bentong",
    )

    canvas_obj.setFillColor(grey_text)
    canvas_obj.setFont(
        "Helvetica-Oblique",
        6,
    )
    canvas_obj.drawCentredString(
        width / 2,
        12.5 * mm,
        "Bentong Municipal Council",
    )

    canvas_obj.setFont(
        "Helvetica",
        5.8,
    )
    canvas_obj.drawCentredString(
        width / 2,
        9.5 * mm,
        "Jalan Ketari, 28700 Bentong, Pahang Darul Makmur",
    )

    canvas_obj.drawCentredString(
        width / 2,
        6.7 * mm,
        "Telefon: 04-5497555 | Aplikasi: TIP Bentong",
    )

    canvas_obj.setFont(
        "Helvetica-Oblique",
        5.4,
    )
    canvas_obj.drawCentredString(
        width / 2,
        4.2 * mm,
        "Telephone: 04-5497555 | Application: TIP Bentong",
    )

    canvas_obj.setFont(
        "Helvetica",
        5.5,
    )
    canvas_obj.drawRightString(
        width - 15 * mm,
        4.2 * mm,
        f"Halaman / Page {document.page}",
    )

    canvas_obj.restoreState()


# =========================================================
# RECEIPT INFORMATION
# =========================================================

def _build_receipt_info(
    paid_date,
    payment_method,
    order_no,
    bank_trx_no,
):
    title = _bilingual_paragraph(
        "Resit",
        "Receipt",
        malay_size=18,
        english_size=10,
        malay_color="#003B8E",
        english_color="#0057D9",
        leading=14,
    )

    order_paragraph = _value_paragraph(
        f"#{_safe_text(order_no)}",
        font_size=9,
        color="#0057D9",
        bold=True,
    )

    left_block = Table(
        [
            [title],
            [order_paragraph],
        ],
        colWidths=[70 * mm],
    )

    left_block.setStyle(
        TableStyle(
            [
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),
            ]
        )
    )

    metadata_rows = [
        [
            _bilingual_paragraph(
                "Dibayar pada",
                "Paid at",
                malay_size=7.5,
                english_size=6.5,
                leading=8,
            ),
            _value_paragraph(
                paid_date.strftime(
                    "%d %b %Y %I:%M %p"
                ),
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
                payment_method,
                font_size=7.5,
                leading=9,
            ),
        ],
    ]

    if bank_trx_no:
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
                    bank_trx_no,
                    font_size=7.5,
                    leading=9,
                ),
            ]
        )

    metadata_table = Table(
        metadata_rows,
        colWidths=[
            43 * mm,
            62 * mm,
        ],
        hAlign="RIGHT",
    )

    metadata_table.setStyle(
        TableStyle(
            [
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
                    3,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
            ]
        )
    )

    info_table = Table(
        [
            [
                left_block,
                metadata_table,
            ]
        ],
        colWidths=[
            70 * mm,
            110 * mm,
        ],
    )

    info_table.setStyle(
        TableStyle(
            [
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
                    0,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
            ]
        )
    )

    return info_table


# =========================================================
# TABLE HEADER
# =========================================================

def _build_table_header():
    header = Table(
        [
            [
                _bilingual_paragraph(
                    "Bil.",
                    "No.",
                    malay_size=7.5,
                    english_size=6.5,
                    malay_color="#FFFFFF",
                    english_color="#DCEBFF",
                    leading=8,
                ),
                _bilingual_paragraph(
                    "Butiran Sewaan",
                    "Rental Details",
                    malay_size=7.5,
                    english_size=6.5,
                    malay_color="#FFFFFF",
                    english_color="#DCEBFF",
                    leading=8,
                ),
                _bilingual_paragraph(
                    "Jumlah Dibayar",
                    "Amount Paid",
                    malay_size=7.5,
                    english_size=6.5,
                    malay_color="#FFFFFF",
                    english_color="#DCEBFF",
                    alignment=TA_RIGHT,
                    leading=8,
                ),
            ]
        ],
        colWidths=[
            12 * mm,
            132 * mm,
            36 * mm,
        ],
    )

    header.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#0057D9"),
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
                    (-1, -1),
                    8,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#0045B0"),
                ),
            ]
        )
    )

    return header


# =========================================================
# RENTAL ITEM ROWS
# Rows continue individually onto the next page.
# The whole account is NOT forced to stay together.
# =========================================================

class RentalContinuationHeader(Table):
    """
    A small account continuation header.

    When ReportLab places the next field row on another page,
    this heading can be inserted before the continued fields
    by building each account as independent flowables.
    """


def _build_account_section_header(
    index,
    account_number,
    amount,
    continued=False,
):
    if continued:
        title_ms = "Sewaan - Sambungan"
        title_en = "Rental - Continued"
    else:
        title_ms = "Sewaan"
        title_en = "Rental"

    header = Table(
        [
            [
                _value_paragraph(
                    str(index),
                    font_size=8,
                    color="#111827",
                    alignment=TA_CENTER,
                    bold=True,
                ),
                _bilingual_paragraph(
                    title_ms,
                    title_en,
                    malay_size=9,
                    english_size=7,
                    malay_color="#003B8E",
                    english_color="#6B7280",
                    leading=10,
                ),
                _value_paragraph(
                    f"RM {_format_money(amount)}",
                    font_size=8,
                    color="#003B8E",
                    alignment=TA_RIGHT,
                    bold=True,
                ),
            ]
        ],
        colWidths=[
            12 * mm,
            132 * mm,
            36 * mm,
        ],
        hAlign="LEFT",
    )

    header.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#EDF4FF"),
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.6,
                    colors.HexColor("#D9E8FF"),
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
                    (-1, -1),
                    8,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
            ]
        )
    )

    return header


def _build_field_row(
    malay_label,
    english_label,
    value,
    shaded=False,
    value_bold=False,
):
    """
    Build one independent field row.

    Because each row is its own flowable, ReportLab moves only
    this row to the next page when there is insufficient space.
    """
    row = Table(
        [
            [
                _bilingual_paragraph(
                    malay_label,
                    english_label,
                    malay_size=7.5,
                    english_size=6.3,
                    malay_color="#0F3F83",
                    english_color="#6B7280",
                    leading=8,
                ),
                _value_paragraph(
                    value,
                    font_size=7.5,
                    leading=9,
                    bold=value_bold,
                ),
            ]
        ],
        colWidths=[
            47 * mm,
            133 * mm,
        ],
        hAlign="LEFT",
        splitByRow=1,
    )

    background = (
        colors.HexColor("#F7FAFF")
        if shaded
        else colors.white
    )

    row.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    background,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.45,
                    colors.HexColor("#D9E8FF"),
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
                    9,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    9,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    # Keep this individual label/value row together.
    return KeepTogether([row])


def _build_rental_item_flowables(
    index,
    item,
):
    """
    Return independent flowables for one rental account.

    The account can continue onto another page. Only a field row
    that cannot fit is moved to the next page.
    """
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

    fields = [
        (
            "Nombor Akaun",
            "Account Number",
            account_number,
            True,
        ),
    ]

    if old_account_number != "-":
        fields.append(
            (
                "Nombor Akaun Lama",
                "Old Account Number",
                old_account_number,
                False,
            )
        )

    fields.extend(
        [
            (
                "Nama Penyewa",
                "Tenant Name",
                tenant_name,
                False,
            ),
            (
                "No. Pendaftaran",
                "Registration No.",
                registration_no,
                False,
            ),
            (
                "Tempoh Sewaan",
                "Rental Period",
                f"{start_date} - {end_date}",
                False,
            ),
            (
                "Alamat Premis",
                "Premise Address",
                premise_address,
                False,
            ),
            (
                "Alamat Surat-Menyurat",
                "Mailing Address",
                mailing_address,
                False,
            ),
            (
                "Tunggakan Sewa",
                "Outstanding Rent",
                f"RM {_format_money(outstanding_rent)}",
                False,
            ),
            (
                "Sewa Semasa",
                "Current Rental Fee",
                f"RM {_format_money(current_rent)}",
                False,
            ),
        ]
    )

    if water_charge > 0:
        fields.append(
            (
                "Caj Air",
                "Water Charge",
                f"RM {_format_money(water_charge)}",
                False,
            )
        )

    if electric_charge > 0:
        fields.append(
            (
                "Caj Elektrik",
                "Electric Charge",
                f"RM {_format_money(electric_charge)}",
                False,
            )
        )

    if management_charge > 0:
        fields.append(
            (
                "Caj Pengurusan",
                "Management Charge",
                f"RM {_format_money(management_charge)}",
                False,
            )
        )

    flowables = [
        _build_account_section_header(
            index=index,
            account_number=account_number,
            amount=amount,
            continued=False,
        ),
    ]

    for field_index, (
        malay_label,
        english_label,
        value,
        value_bold,
    ) in enumerate(fields):
        flowables.append(
            _build_field_row(
                malay_label=malay_label,
                english_label=english_label,
                value=value,
                shaded=field_index % 2 == 1,
                value_bold=value_bold,
            )
        )

    flowables.append(
        Spacer(1, 5 * mm)
    )

    return flowables


# =========================================================
# TOTAL AND REMINDER
# =========================================================

def _build_total_block(total_amount):
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
                    font_size=15,
                    color="#FFFFFF",
                    alignment=TA_RIGHT,
                    bold=True,
                ),
            ]
        ],
        colWidths=[
            115 * mm,
            65 * mm,
        ],
    )

    total_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#003B8E"),
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

    reminder_style = ParagraphStyle(
        name="Reminder",
        fontName="Helvetica",
        fontSize=6.8,
        leading=9,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#666666"),
        spaceBefore=0,
        spaceAfter=0,
    )

    reminder = Paragraph(
        (
            '<font name="Helvetica-Bold">'
            "Sila maklum bahawa kemas kini baki akaun mungkin "
            "diproses pada hari bekerja berikutnya."
            "</font>"
            "<br/>"
            '<font name="Helvetica-Oblique">'
            "Please be informed that account balance updates "
            "may be processed on the following working day."
            "</font>"
        ),
        reminder_style,
    )

    return KeepTogether(
        [
            total_table,
            Spacer(1, 5 * mm),
            reminder,
        ]
    )


# =========================================================
# SEWAAN RECEIPT GENERATOR
# =========================================================

def generate_sewaan_receipt_bentong(
    paid_date: datetime.datetime,
    payment_method: str,
    sewaan_items: list = None,
    order_no: str = None,
    bank_trx_no: str = None,
):
    """
    Generate a responsive rental receipt.

    Key behavior:
    - No manually estimated item height.
    - Long values wrap automatically.
    - The whole rental account is NOT forced to stay together.
    - Each individual label/value row stays together.
    - When a row cannot fit, only that row moves to the next page.
    - The same account then continues normally on the next page.
    - Header and footer repeat on every page.
    - No blank metadata-only page caused by oversized row estimates.
    """

    if sewaan_items is None:
        sewaan_items = []

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=50 * mm,
        bottomMargin=24 * mm,
        title=(
            "Resit Bayaran Sewaan / "
            "Rental Payment Receipt"
        ),
        author="TIP Bentong",
    )

    story = []

    # Receipt metadata
    story.append(
        _build_receipt_info(
            paid_date=paid_date,
            payment_method=_safe_text(
                payment_method
            ),
            order_no=order_no,
            bank_trx_no=bank_trx_no,
        )
    )

    story.append(
        Spacer(1, 7 * mm)
    )

    # Table header
    story.append(
        _build_table_header()
    )

    story.append(
        Spacer(1, 4 * mm)
    )

    total_amount = 0.0

    for index, item in enumerate(
        sewaan_items,
        start=1,
    ):
        total_amount += _safe_float(
            item.get("amount")
        )

        story.extend(
            _build_rental_item_flowables(
                index=index,
                item=item,
            )
        )

    story.append(
        Spacer(1, 3 * mm)
    )

    story.append(
        _build_total_block(
            total_amount
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
        "tunggakan_sewa": "400.00",
        "sewa_semasa": "",
        "tunggakan_caj_air": "20",
        "caj_air_semasa": "",
        "tunggakan_caj_elektrik": "10",
        "caj_elektrik_semasa": "",
        "tunggakan_caj_pengurusan": "5",
        "caj_pengurusan_semasa": "",
        "jumlah": "535.00",
        "jumlah_setahun": "1100.000000",
    }

    api_data_2 = {
        "account_no": (
            "S0602000081402-LONG-ACCOUNT-"
            "NUMBER-FOR-WRAPPING-TEST"
        ),
        "old_account_no": "",
        "name": (
            "TEST TENANT WITH A VERY LONG "
            "NAME FOR WRAPPING"
        ),
        "start_date": "2025-09-01",
        "end_date": "2025-09-30",
        "rental_fee": "150.000000",
        "rent_alamatswn": "NO. 2",
        "rent_jalanname": (
            "DATARAN NIAGA KARAK WITH A LONG "
            "PREMISE ADDRESS FOR TESTING"
        ),
        "rent_postcode": "",
        "rent_bandarnam": "KARAK",
        "rent_negeri": "",
        "rent_pdaftaran": "800101015555",
        "alamat1": "NO. 10",
        "alamat2": (
            "TAMAN CONTOH DENGAN ALAMAT "
            "SURAT MENYURAT YANG PANJANG"
        ),
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