from datetime import date, timedelta
from io import BytesIO
import html

import qrcode
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fpdf import FPDF
from sqlalchemy.orm import Session

from app.controllers.licenses.licenses_receipt import generate_multi_license_pdf
from app.db.database import get_db
from app.models.licenses.licenses_model import (
    LicenseCreate,
    LicenseResponse,
    OwnerLicenseCreate,
    OwnerLicenseResponse,
)
from app.schema.licenses.licenses_schema import License, OwnerLicense
from app.utils.blob_upload import upload_to_blob


router = APIRouter(
    prefix="/license",
    tags=["License"],
)


# =========================================================
# HELPERS
# =========================================================

def _safe_html(value, fallback="-"):
    if value is None:
        return fallback

    text = str(value).strip()

    if not text:
        return fallback

    return html.escape(text)


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
        return _safe_html(value)


def _generate_qr_response(url):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )

    qr.add_data(url)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white",
    )

    buffer = BytesIO()
    image.save(buffer, "PNG")
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="image/png",
    )


def _build_single_license_html(
    license_obj,
    owner_name,
    pdf_url,
):
    return f"""
<!DOCTYPE html>
<html lang="ms">
<head>
    <meta charset="utf-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >

    <meta name="color-scheme" content="only light">

    <title>
        E-Resit Lesen /
        License E-Receipt
    </title>

    <style>
        * {{
            box-sizing: border-box;
        }}

        html {{
            color-scheme: only light;
            background: #eef3f8;
        }}

        body {{
            margin: 0;
            padding: 28px 16px;
            min-height: 100vh;
            background:
                linear-gradient(
                    180deg,
                    #eaf2ff 0%,
                    #f7f9fc 100%
                );
            color: #111827;
            font-family:
                "Segoe UI",
                Arial,
                sans-serif;
        }}

        .page {{
            width: 100%;
            max-width: 860px;
            margin: 0 auto;
        }}

        .receipt {{
            background: #ffffff;
            border: 1px solid #dfe7f2;
            border-radius: 22px;
            overflow: hidden;
            box-shadow:
                0 18px 45px
                rgba(15, 23, 42, 0.12);
        }}

        .header {{
            position: relative;
            overflow: hidden;
            padding: 34px 30px;
            text-align: center;
            color: #ffffff;
            background:
                linear-gradient(
                    135deg,
                    #003b8e,
                    #0a66d8
                );
        }}

        .header::after {{
            content: "";
            position: absolute;
            width: 220px;
            height: 220px;
            right: -70px;
            top: -90px;
            border-radius: 50%;
            background:
                rgba(255, 255, 255, 0.08);
        }}

        .header-content {{
            position: relative;
            z-index: 1;
        }}

        .ms {{
            font-weight: 700;
        }}

        .en {{
            margin-top: 3px;
            font-style: italic;
            font-weight: 400;
            color: #6b7280;
            font-size: 0.88em;
        }}

        .header .ms {{
            color: #ffffff;
        }}

        .header .en {{
            color:
                rgba(
                    255,
                    255,
                    255,
                    0.86
                );
        }}

        .title .ms {{
            font-size: 30px;
            line-height: 1.1;
        }}

        .title .en {{
            margin-top: 7px;
            font-size: 17px;
        }}

        .subtitle {{
            margin-top: 15px;
        }}

        .subtitle .ms {{
            font-size: 14px;
        }}

        .subtitle .en {{
            font-size: 12px;
        }}

        .content {{
            padding: 30px;
        }}

        .summary-grid {{
            display: grid;
            grid-template-columns:
                repeat(2, minmax(0, 1fr));
            gap: 16px;
        }}

        .summary-card {{
            padding: 16px;
            border: 1px solid #dce8f8;
            border-radius: 14px;
            background: #f8fbff;
        }}

        .summary-card.full {{
            grid-column: 1 / -1;
        }}

        .label {{
            margin-bottom: 8px;
        }}

        .label .ms {{
            color: #0f3f83;
            font-size: 14px;
        }}

        .label .en {{
            font-size: 12px;
        }}

        .value {{
            color: #111827;
            font-size: 16px;
            font-weight: 600;
            line-height: 1.45;
            word-break: break-word;
        }}

        .amount-card {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 20px;
            margin-top: 22px;
            padding: 20px 22px;
            border: 1px solid #bfd7ff;
            border-left: 6px solid #0a66d8;
            border-radius: 16px;
            background:
                linear-gradient(
                    135deg,
                    #eaf3ff,
                    #f5f9ff
                );
        }}

        .amount-label .ms {{
            color: #0f3f83;
            font-size: 17px;
        }}

        .amount-label .en {{
            font-size: 13px;
        }}

        .amount-value {{
            color: #0a56c2;
            font-size: 30px;
            font-weight: 800;
            white-space: nowrap;
        }}

        .thank-you {{
            margin-top: 28px;
            text-align: center;
            color: #15803d;
        }}

        .thank-you .ms {{
            font-size: 19px;
        }}

        .thank-you .en {{
            color: #2f855a;
            font-size: 14px;
        }}

        .pdf-button {{
            margin-top: 28px;
            text-align: center;
        }}

        .pdf-button a {{
            display: inline-block;
            min-width: 260px;
            padding: 14px 24px;
            border-radius: 12px;
            background:
                linear-gradient(
                    135deg,
                    #16a34a,
                    #22c55e
                );
            color: #ffffff;
            text-decoration: none;
            box-shadow:
                0 8px 18px
                rgba(34, 197, 94, 0.25);
        }}

        .pdf-button .ms,
        .pdf-button .en {{
            color: #ffffff;
        }}

        .footer {{
            margin-top: 30px;
            padding-top: 22px;
            border-top: 1px solid #e5e7eb;
            text-align: center;
            color: #6b7280;
            font-size: 13px;
            line-height: 1.5;
        }}

        .footer .ms {{
            color: #374151;
        }}

        @media (max-width: 680px) {{
            body {{
                padding: 12px;
            }}

            .header {{
                padding: 28px 18px;
            }}

            .title .ms {{
                font-size: 24px;
            }}

            .title .en {{
                font-size: 15px;
            }}

            .content {{
                padding: 20px 16px;
            }}

            .summary-grid {{
                grid-template-columns: 1fr;
            }}

            .summary-card.full {{
                grid-column: auto;
            }}

            .amount-card {{
                display: block;
                text-align: center;
            }}

            .amount-value {{
                margin-top: 10px;
                font-size: 27px;
            }}

            .pdf-button a {{
                width: 100%;
                min-width: 0;
            }}
        }}

        @media print {{
            body {{
                padding: 0;
                background: #ffffff;
            }}

            .receipt {{
                border: none;
                border-radius: 0;
                box-shadow: none;
            }}

            .pdf-button {{
                display: none;
            }}
        }}
    </style>
</head>

<body>
    <div class="page">
        <div class="receipt">
            <div class="header">
                <div class="header-content">
                    <div class="title">
                        <div class="ms">
                            E-Resit Lesen
                        </div>

                        <div class="en">
                            License E-Receipt
                        </div>
                    </div>

                    <div class="subtitle">
                        <div class="ms">
                            Rekod Transaksi Rasmi
                        </div>

                        <div class="en">
                            Official Transaction Record
                        </div>
                    </div>
                </div>
            </div>

            <div class="content">
                <div class="summary-grid">
                    <div class="summary-card">
                        <div class="label">
                            <div class="ms">
                                No. Lesen
                            </div>

                            <div class="en">
                                License No.
                            </div>
                        </div>

                        <div class="value">
                            {_safe_html(license_obj.licensenum)}
                        </div>
                    </div>

                    <div class="summary-card">
                        <div class="label">
                            <div class="ms">
                                Jenis Lesen
                            </div>

                            <div class="en">
                                License Type
                            </div>
                        </div>

                        <div class="value">
                            {_safe_html(license_obj.licensetype)}
                        </div>
                    </div>

                    <div class="summary-card">
                        <div class="label">
                            <div class="ms">
                                No. IC Pemilik
                            </div>

                            <div class="en">
                                Owner IC
                            </div>
                        </div>

                        <div class="value">
                            {_safe_html(license_obj.ic)}
                        </div>
                    </div>

                    <div class="summary-card">
                        <div class="label">
                            <div class="ms">
                                Nama Pemilik
                            </div>

                            <div class="en">
                                Owner Name
                            </div>
                        </div>

                        <div class="value">
                            {_safe_html(owner_name)}
                        </div>
                    </div>

                    <div class="summary-card">
                        <div class="label">
                            <div class="ms">
                                Tarikh Mula
                            </div>

                            <div class="en">
                                Start Date
                            </div>
                        </div>

                        <div class="value">
                            {_format_date(license_obj.start_date)}
                        </div>
                    </div>

                    <div class="summary-card">
                        <div class="label">
                            <div class="ms">
                                Tarikh Tamat
                            </div>

                            <div class="en">
                                End Date
                            </div>
                        </div>

                        <div class="value">
                            {_format_date(license_obj.end_date)}
                        </div>
                    </div>
                </div>

                <div class="amount-card">
                    <div class="amount-label">
                        <div class="ms">
                            Jumlah Dibayar
                        </div>

                        <div class="en">
                            Total Paid
                        </div>
                    </div>

                    <div class="amount-value">
                        RM {_safe_amount(license_obj.amount):,.2f}
                    </div>
                </div>

                <div class="thank-you">
                    <div class="ms">
                        Terima kasih atas pembayaran anda.
                    </div>

                    <div class="en">
                        Thank you for your payment.
                    </div>
                </div>

                <div class="pdf-button">
                    <a
                        href="{pdf_url}"
                        target="_blank"
                    >
                        <div class="ms">
                            Muat Turun Resit PDF
                        </div>

                        <div class="en">
                            Download PDF Receipt
                        </div>
                    </a>
                </div>

                <div class="footer">
                    <div class="ms">
                        © 2026 Juara Inovasi Pintar System
                        · Hak Cipta Terpelihara
                    </div>

                    <div class="en">
                        All Rights Reserved
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""


def _build_multi_license_html(
    licenses_data,
    total_amount,
    pdf_url,
):
    rows_html = ""

    for license_item in licenses_data:
        rows_html += f"""
        <tr>
            <td>
                {_safe_html(license_item.get("licensenumber"))}
            </td>

            <td>
                {_safe_html(license_item.get("licensetype"))}
            </td>

            <td>
                {_format_date(license_item.get("expired_date"))}
            </td>

            <td class="money">
                RM {_safe_amount(license_item.get("amount")):,.2f}
            </td>
        </tr>
        """

    return f"""
<!DOCTYPE html>
<html lang="ms">
<head>
    <meta charset="utf-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >

    <meta name="color-scheme" content="only light">

    <title>
        Resit Pelbagai Lesen /
        Multiple License Receipt
    </title>

    <style>
        * {{
            box-sizing: border-box;
        }}

        html {{
            color-scheme: only light;
            background: #eef3f8;
        }}

        body {{
            margin: 0;
            padding: 28px 16px;
            min-height: 100vh;
            background:
                linear-gradient(
                    180deg,
                    #eaf2ff 0%,
                    #f7f9fc 100%
                );
            color: #111827;
            font-family:
                "Segoe UI",
                Arial,
                sans-serif;
        }}

        .page {{
            width: 100%;
            max-width: 980px;
            margin: 0 auto;
        }}

        .receipt {{
            background: #ffffff;
            border: 1px solid #dfe7f2;
            border-radius: 22px;
            overflow: hidden;
            box-shadow:
                0 18px 45px
                rgba(15, 23, 42, 0.12);
        }}

        .header {{
            position: relative;
            overflow: hidden;
            padding: 34px 30px;
            text-align: center;
            color: #ffffff;
            background:
                linear-gradient(
                    135deg,
                    #003b8e,
                    #0a66d8
                );
        }}

        .header::after {{
            content: "";
            position: absolute;
            width: 220px;
            height: 220px;
            right: -70px;
            top: -90px;
            border-radius: 50%;
            background:
                rgba(255, 255, 255, 0.08);
        }}

        .header-content {{
            position: relative;
            z-index: 1;
        }}

        .ms {{
            font-weight: 700;
        }}

        .en {{
            margin-top: 3px;
            font-style: italic;
            font-weight: 400;
            color: #6b7280;
            font-size: 0.88em;
        }}

        .header .ms {{
            color: #ffffff;
        }}

        .header .en {{
            color:
                rgba(
                    255,
                    255,
                    255,
                    0.86
                );
        }}

        .title .ms {{
            font-size: 30px;
            line-height: 1.1;
        }}

        .title .en {{
            margin-top: 7px;
            font-size: 17px;
        }}

        .subtitle {{
            margin-top: 15px;
        }}

        .content {{
            padding: 30px;
        }}

        .table-container {{
            width: 100%;
            overflow-x: auto;
            border: 1px solid #dce8f8;
            border-radius: 14px;
        }}

        table {{
            width: 100%;
            min-width: 760px;
            border-collapse: collapse;
        }}

        th {{
            padding: 14px 13px;
            text-align: left;
            vertical-align: middle;
            color: #ffffff;
            background: #0a66d8;
        }}

        th .ms {{
            color: #ffffff;
        }}

        th .en {{
            color:
                rgba(
                    255,
                    255,
                    255,
                    0.85
                );
            font-size: 11px;
        }}

        td {{
            padding: 14px 13px;
            border-bottom: 1px solid #e5e7eb;
            vertical-align: top;
            font-size: 14px;
        }}

        tbody tr:nth-child(even) {{
            background: #f8fbff;
        }}

        tbody tr:last-child td {{
            border-bottom: none;
        }}

        .money {{
            text-align: right;
            white-space: nowrap;
            color: #0a56c2;
            font-weight: 700;
        }}

        .total-card {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 20px;
            margin-top: 22px;
            padding: 20px 22px;
            border: 1px solid #bfd7ff;
            border-left: 6px solid #0a66d8;
            border-radius: 16px;
            background:
                linear-gradient(
                    135deg,
                    #eaf3ff,
                    #f5f9ff
                );
        }}

        .total-label .ms {{
            color: #0f3f83;
            font-size: 17px;
        }}

        .total-label .en {{
            font-size: 13px;
        }}

        .total-value {{
            color: #0a56c2;
            font-size: 30px;
            font-weight: 800;
            white-space: nowrap;
        }}

        .thank-you {{
            margin-top: 28px;
            text-align: center;
            color: #15803d;
        }}

        .thank-you .ms {{
            font-size: 19px;
        }}

        .thank-you .en {{
            color: #2f855a;
            font-size: 14px;
        }}

        .pdf-button {{
            margin-top: 28px;
            text-align: center;
        }}

        .pdf-button a {{
            display: inline-block;
            min-width: 260px;
            padding: 14px 24px;
            border-radius: 12px;
            background:
                linear-gradient(
                    135deg,
                    #16a34a,
                    #22c55e
                );
            color: #ffffff;
            text-decoration: none;
            box-shadow:
                0 8px 18px
                rgba(34, 197, 94, 0.25);
        }}

        .pdf-button .ms,
        .pdf-button .en {{
            color: #ffffff;
        }}

        .footer {{
            margin-top: 30px;
            padding-top: 22px;
            border-top: 1px solid #e5e7eb;
            text-align: center;
            color: #6b7280;
            font-size: 13px;
            line-height: 1.5;
        }}

        .footer .ms {{
            color: #374151;
        }}

        @media (max-width: 680px) {{
            body {{
                padding: 12px;
            }}

            .header {{
                padding: 28px 18px;
            }}

            .title .ms {{
                font-size: 24px;
            }}

            .title .en {{
                font-size: 15px;
            }}

            .content {{
                padding: 20px 16px;
            }}

            .total-card {{
                display: block;
                text-align: center;
            }}

            .total-value {{
                margin-top: 10px;
                font-size: 27px;
            }}

            .pdf-button a {{
                width: 100%;
                min-width: 0;
            }}
        }}
    </style>
</head>

<body>
    <div class="page">
        <div class="receipt">
            <div class="header">
                <div class="header-content">
                    <div class="title">
                        <div class="ms">
                            Resit Pelbagai Lesen
                        </div>

                        <div class="en">
                            Multiple License Receipt
                        </div>
                    </div>

                    <div class="subtitle">
                        <div class="ms">
                            Rekod Transaksi Rasmi
                        </div>

                        <div class="en">
                            Official Transaction Record
                        </div>
                    </div>
                </div>
            </div>

            <div class="content">
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>
                                    <div class="ms">
                                        No. Lesen
                                    </div>

                                    <div class="en">
                                        License Number
                                    </div>
                                </th>

                                <th>
                                    <div class="ms">
                                        Jenis Lesen
                                    </div>

                                    <div class="en">
                                        License Type
                                    </div>
                                </th>

                                <th>
                                    <div class="ms">
                                        Tarikh Luput
                                    </div>

                                    <div class="en">
                                        Expiry Date
                                    </div>
                                </th>

                                <th style="text-align: right;">
                                    <div class="ms">
                                        Jumlah (RM)
                                    </div>

                                    <div class="en">
                                        Amount (RM)
                                    </div>
                                </th>
                            </tr>
                        </thead>

                        <tbody>
                            {rows_html}
                        </tbody>
                    </table>
                </div>

                <div class="total-card">
                    <div class="total-label">
                        <div class="ms">
                            Jumlah Keseluruhan
                        </div>

                        <div class="en">
                            Total Amount
                        </div>
                    </div>

                    <div class="total-value">
                        RM {_safe_amount(total_amount):,.2f}
                    </div>
                </div>

                <div class="thank-you">
                    <div class="ms">
                        Terima kasih atas pembayaran anda.
                    </div>

                    <div class="en">
                        Thank you for your payment.
                    </div>
                </div>

                <div class="pdf-button">
                    <a
                        href="{pdf_url}"
                        target="_blank"
                    >
                        <div class="ms">
                            Muat Turun Resit PDF
                        </div>

                        <div class="en">
                            Download PDF Receipt
                        </div>
                    </a>
                </div>

                <div class="footer">
                    <div class="ms">
                        © 2026 Juara Inovasi Pintar System
                        · Hak Cipta Terpelihara
                    </div>

                    <div class="en">
                        All Rights Reserved
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""


# =========================================================
# OWNER ENDPOINTS
# =========================================================

@router.post(
    "/owner",
    response_model=OwnerLicenseResponse,
)
def create_owner(
    owner: OwnerLicenseCreate,
    db: Session = Depends(get_db),
):
    existing = (
        db.query(OwnerLicense)
        .filter(OwnerLicense.ic == owner.ic)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail=(
                "Pemilik dengan nombor IC ini telah wujud / "
                "Owner with this IC already exists"
            ),
        )

    new_owner = OwnerLicense(
        ic=owner.ic,
        name=owner.name,
        email=owner.email,
        address=owner.address,
    )

    db.add(new_owner)
    db.commit()
    db.refresh(new_owner)

    return new_owner


# =========================================================
# CREATE LICENSE
# =========================================================

@router.post(
    "/",
    response_model=LicenseResponse,
)
def create_license(
    license: LicenseCreate,
    db: Session = Depends(get_db),
):
    owner = (
        db.query(OwnerLicense)
        .filter(OwnerLicense.ic == license.ic)
        .first()
    )

    if not owner:
        raise HTTPException(
            status_code=404,
            detail=(
                "Pemilik tidak dijumpai / "
                "Owner not found"
            ),
        )

    if "BIZ" in license.licensenum:
        license_type = (
            "Lesen Perniagaan / "
            "Business License"
        )

    elif "HBR" in license.licensenum:
        license_type = (
            "Lesen Hiburan / Penghibur Jalanan / "
            "Entertainment / Buskers License"
        )

    elif "IKL" in license.licensenum:
        license_type = (
            "Lesen Iklan / "
            "Advertisement License"
        )

    elif "KOM" in license.licensenum:
        license_type = (
            "Lesen Komposit / "
            "Composite License"
        )

    else:
        license_type = (
            "Tidak Diketahui / "
            "Unknown"
        )

    today = date.today()
    end_date = today + timedelta(days=365)

    new_license = License(
        licensenum=license.licensenum,
        licensetype=license_type,
        ic=license.ic,
        amount=license.amount,
        start_date=today,
        end_date=end_date,
    )

    db.add(new_license)
    db.commit()
    db.refresh(new_license)

    return new_license


# =========================================================
# PAY SINGLE LICENSE
# =========================================================

@router.post(
    "/pay/{licensenum}",
    response_model=LicenseResponse,
)
def pay_license(
    licensenum: str,
    db: Session = Depends(get_db),
):
    license_obj = (
        db.query(License)
        .filter(License.licensenum == licensenum)
        .first()
    )

    if not license_obj:
        raise HTTPException(
            status_code=404,
            detail=(
                "Lesen tidak dijumpai / "
                "License not found"
            ),
        )

    today = date.today()

    if (
        not license_obj.end_date
        or license_obj.end_date < today
    ):
        license_obj.start_date = today
        license_obj.end_date = (
            today + timedelta(days=365)
        )

    else:
        license_obj.end_date = (
            license_obj.end_date
            + timedelta(days=365)
        )

    db.commit()
    db.refresh(license_obj)

    return license_obj


# =========================================================
# GET ALL LICENSES
# =========================================================

@router.get(
    "/",
    response_model=list[LicenseResponse],
)
def get_licenses(
    db: Session = Depends(get_db),
):
    return db.query(License).all()


# =========================================================
# PAY MULTIPLE LICENSES
# =========================================================

@router.post("/pay-multi")
def pay_multiple_licenses(
    payload: dict,
    db: Session = Depends(get_db),
):
    license_numbers = payload.get("licenses")

    if not isinstance(
        license_numbers,
        list,
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "licenses mesti dalam bentuk senarai nombor lesen / "
                "licenses must be a list of license numbers"
            ),
        )

    license_numbers = [
        str(license_number).strip()
        for license_number in license_numbers
        if str(license_number).strip()
    ]

    if not license_numbers:
        raise HTTPException(
            status_code=400,
            detail=(
                "Tiada nombor lesen yang sah diberikan / "
                "No valid license numbers provided"
            ),
        )

    today = date.today()
    updated_licenses = []
    total_amount = 0.0

    for license_number in license_numbers:
        license_obj = (
            db.query(License)
            .filter(
                License.licensenum
                == license_number
            )
            .first()
        )

        if not license_obj:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Lesen {license_number} tidak dijumpai / "
                    f"License {license_number} not found"
                ),
            )

        if (
            not license_obj.end_date
            or license_obj.end_date < today
        ):
            license_obj.start_date = today
            license_obj.end_date = (
                today + timedelta(days=365)
            )

        else:
            license_obj.end_date = (
                license_obj.end_date
                + timedelta(days=365)
            )

        total_amount += _safe_amount(
            license_obj.amount
        )

        updated_licenses.append(
            license_obj
        )

    db.commit()

    for license_obj in updated_licenses:
        db.refresh(license_obj)

    return {
        "message": (
            "Pembayaran pelbagai lesen berjaya / "
            "Multiple licenses paid successfully"
        ),
        "total_amount": round(
            total_amount,
            2,
        ),
        "count": len(updated_licenses),
    }


# =========================================================
# GET SINGLE LICENSE
# =========================================================

@router.get(
    "/{licensenum}",
    response_model=LicenseResponse,
)
def get_license(
    licensenum: str,
    db: Session = Depends(get_db),
):
    license_obj = (
        db.query(License)
        .filter(License.licensenum == licensenum)
        .first()
    )

    if not license_obj:
        raise HTTPException(
            status_code=404,
            detail=(
                "Lesen tidak dijumpai / "
                "License not found"
            ),
        )

    return license_obj


# =========================================================
# SINGLE LICENSE RECEIPT
# =========================================================

@router.get(
    "/receipt/qr/{licensenum}",
    response_class=HTMLResponse,
)
def view_license_receipt(
    licensenum: str,
    db: Session = Depends(get_db),
):
    license_obj = (
        db.query(License)
        .filter(License.licensenum == licensenum)
        .first()
    )

    if not license_obj:
        raise HTTPException(
            status_code=404,
            detail=(
                "Lesen tidak dijumpai / "
                "License not found"
            ),
        )

    owner = (
        db.query(OwnerLicense)
        .filter(OwnerLicense.ic == license_obj.ic)
        .first()
    )

    owner_name = (
        owner.name
        if owner
        else "N/A"
    )

    pdf = FPDF()
    pdf.add_page()

    pdf.set_font(
        "Arial",
        "B",
        16,
    )

    pdf.cell(
        0,
        10,
        "E-Resit Lesen / License E-Receipt",
        ln=True,
        align="C",
    )

    pdf.ln(10)

    pdf.set_font(
        "Arial",
        "",
        12,
    )

    pdf.cell(
        0,
        8,
        (
            f"No. Lesen / License No: "
            f"{license_obj.licensenum}"
        ),
        ln=True,
    )

    pdf.cell(
        0,
        8,
        (
            f"Jenis Lesen / License Type: "
            f"{license_obj.licensetype}"
        ),
        ln=True,
    )

    pdf.cell(
        0,
        8,
        (
            f"No. IC Pemilik / Owner IC: "
            f"{license_obj.ic}"
        ),
        ln=True,
    )

    pdf.cell(
        0,
        8,
        (
            f"Nama Pemilik / Owner Name: "
            f"{owner_name}"
        ),
        ln=True,
    )

    pdf.cell(
        0,
        8,
        (
            f"Jumlah / Amount: "
            f"RM {_safe_amount(license_obj.amount):.2f}"
        ),
        ln=True,
    )

    pdf.cell(
        0,
        8,
        (
            f"Tarikh Mula / Start Date: "
            f"{_format_date(license_obj.start_date)}"
        ),
        ln=True,
    )

    pdf.cell(
        0,
        8,
        (
            f"Tarikh Tamat / End Date: "
            f"{_format_date(license_obj.end_date)}"
        ),
        ln=True,
    )

    pdf_bytes = (
        pdf.output(dest="S")
        .encode("latin1")
    )

    pdf_filename = (
        f"license_{license_obj.licensenum}.pdf"
    )

    pdf_url = upload_to_blob(
        pdf_filename,
        pdf_bytes,
        content_type="application/pdf",
    )

    receipt_html = _build_single_license_html(
        license_obj,
        owner_name,
        pdf_url,
    )

    return HTMLResponse(
        content=receipt_html
    )


# =========================================================
# MULTIPLE LICENSE RECEIPT QR
# =========================================================

@router.post("/receipt/qr/multi")
def generate_multi_license_receipt(
    payload: dict,
    db: Session = Depends(get_db),
):
    license_numbers = payload.get(
        "licenses",
        [],
    )

    if not license_numbers:
        raise HTTPException(
            status_code=400,
            detail=(
                "Tiada nombor lesen diberikan / "
                "No license numbers provided"
            ),
        )

    licenses_data = []
    total_amount = 0.0

    for license_number in license_numbers:
        license_obj = (
            db.query(License)
            .filter(
                License.licensenum
                == license_number
            )
            .first()
        )

        if not license_obj:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Lesen {license_number} tidak dijumpai / "
                    f"License {license_number} not found"
                ),
            )

        owner = (
            db.query(OwnerLicense)
            .filter(
                OwnerLicense.ic
                == license_obj.ic
            )
            .first()
        )

        owner_name = (
            owner.name
            if owner
            else "N/A"
        )

        licenses_data.append(
            {
                "licensenumber": (
                    license_obj.licensenum
                ),
                "licensetype": (
                    license_obj.licensetype
                ),
                "expired_date": (
                    license_obj.end_date
                ),
                "amount": (
                    license_obj.amount
                ),
                "owner_name": owner_name,
                "ic": license_obj.ic,
            }
        )

        total_amount += _safe_amount(
            license_obj.amount
        )

    pdf_buffer = generate_multi_license_pdf(
        licenses_data,
        total_amount,
    )

    pdf_filename = (
        "multi_license_receipt.pdf"
    )

    pdf_url = upload_to_blob(
        pdf_filename,
        pdf_buffer.getvalue(),
        content_type="application/pdf",
    )

    receipt_html = _build_multi_license_html(
        licenses_data,
        total_amount,
        pdf_url,
    )

    html_filename = (
        "multi_license_receipt.html"
    )

    html_url = upload_to_blob(
        html_filename,
        receipt_html.encode("utf-8"),
        content_type="text/html",
    )

    return _generate_qr_response(
        html_url
    )


# =========================================================
# GET LICENSES BY OWNER IC
# =========================================================

@router.get(
    "/by-ic/{ic}",
    response_model=list[LicenseResponse],
)
def get_licenses_by_ic(
    ic: str,
    db: Session = Depends(get_db),
):
    owner = (
        db.query(OwnerLicense)
        .filter(OwnerLicense.ic == ic)
        .first()
    )

    if not owner:
        raise HTTPException(
            status_code=404,
            detail=(
                "Pemilik tidak dijumpai / "
                "Owner not found"
            ),
        )

    licenses = (
        db.query(License)
        .filter(License.ic == ic)
        .all()
    )

    return licenses