from io import BytesIO
import html

import qrcode
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.controllers.compound.compound_receipt import (
    generate_multi_compound_pdf,
    generate_single_compound_pdf,
)
from app.db.database import get_db
from app.models.compound.compound_model import (
    CompoundCreate,
    CompoundResponse,
    StatusTypeEnum,
)
from app.models.compound.multicompound_model import (
    MultiCompoundCreate,
    MultiCompoundResponse,
)
from app.schema.compound.compound_schema import Compound, MultiCompound
from app.utils.blob_upload import upload_to_blob


router = APIRouter(
    prefix="/compound",
    tags=["Compound"],
)


# =====================================================
# HELPERS
# =====================================================

def safe_html(value, fallback="-"):
    if value is None:
        return fallback

    text = str(value).strip()

    if not text:
        return fallback

    return html.escape(text)


def safe_amount(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def format_date(value):
    if value is None:
        return "-"

    try:
        return value.strftime("%d/%m/%Y")
    except (AttributeError, ValueError):
        return safe_html(value)


def format_time(value):
    if value is None:
        return "-"

    try:
        return value.strftime("%I:%M %p")
    except (AttributeError, ValueError):
        return safe_html(value)


def generate_qr_response(receipt_url: str):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )

    qr.add_data(receipt_url)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white",
    )

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="image/png",
    )


def build_single_compound_html(
    compound_name,
    compound_no,
    compound_plate,
    compound_date,
    compound_time,
    compound_offense,
    compound_amount,
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
        E-Resit Kompaun /
        Compound E-Receipt
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

        .thankyou {{
            margin-top: 28px;
            text-align: center;
            color: #15803d;
        }}

        .thankyou .ms {{
            font-size: 19px;
        }}

        .thankyou .en {{
            color: #2f855a;
            font-size: 14px;
        }}

        .download-btn {{
            margin-top: 28px;
            text-align: center;
        }}

        .download-btn a {{
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

        .download-btn .ms,
        .download-btn .en {{
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

            .download-btn a {{
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
                            E-Resit Kompaun
                        </div>

                        <div class="en">
                            Compound E-Receipt
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
                            <div class="ms">Nama</div>
                            <div class="en">Name</div>
                        </div>

                        <div class="value">
                            {compound_name}
                        </div>
                    </div>

                    <div class="summary-card">
                        <div class="label">
                            <div class="ms">
                                No. Kompaun
                            </div>

                            <div class="en">
                                Compound No.
                            </div>
                        </div>

                        <div class="value">
                            {compound_no}
                        </div>
                    </div>

                    <div class="summary-card">
                        <div class="label">
                            <div class="ms">
                                No. Plat
                            </div>

                            <div class="en">
                                Plate No.
                            </div>
                        </div>

                        <div class="value">
                            {compound_plate}
                        </div>
                    </div>

                    <div class="summary-card">
                        <div class="label">
                            <div class="ms">
                                Tarikh
                            </div>

                            <div class="en">
                                Date
                            </div>
                        </div>

                        <div class="value">
                            {compound_date}
                        </div>
                    </div>

                    <div class="summary-card">
                        <div class="label">
                            <div class="ms">
                                Masa
                            </div>

                            <div class="en">
                                Time
                            </div>
                        </div>

                        <div class="value">
                            {compound_time}
                        </div>
                    </div>

                    <div class="summary-card full">
                        <div class="label">
                            <div class="ms">
                                Kesalahan
                            </div>

                            <div class="en">
                                Offense
                            </div>
                        </div>

                        <div class="value">
                            {compound_offense}
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
                        RM {compound_amount:,.2f}
                    </div>
                </div>

                <div class="thankyou">
                    <div class="ms">
                        Terima kasih atas pembayaran anda.
                    </div>

                    <div class="en">
                        Thank you for your payment.
                    </div>
                </div>

                <div class="download-btn">
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
                        © 2026 Juara Inovasi Pasifik System
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


def build_multi_compound_html(
    compounds,
    total_amount,
    pdf_url,
):
    rows_html = ""

    for compound in compounds:
        compound_number = safe_html(
            compound.get("compoundnum")
        )

        amount = safe_amount(
            compound.get("amount")
        )

        rows_html += f"""
        <tr>
            <td>{compound_number}</td>

            <td class="money">
                RM {amount:,.2f}
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
        Resit Pelbagai Kompaun /
        Multiple Compound Receipt
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
            max-width: 900px;
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
            min-width: 560px;
            border-collapse: collapse;
        }}

        th {{
            padding: 14px 13px;
            text-align: left;
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

        .thankyou {{
            margin-top: 28px;
            text-align: center;
            color: #15803d;
        }}

        .thankyou .ms {{
            font-size: 19px;
        }}

        .thankyou .en {{
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
                            Resit Pelbagai Kompaun
                        </div>

                        <div class="en">
                            Multiple Compound Receipt
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
                                        No. Kompaun
                                    </div>

                                    <div class="en">
                                        Compound Number
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
                        RM {safe_amount(total_amount):,.2f}
                    </div>
                </div>

                <div class="thankyou">
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
                        © 2026 Juara Inovasi Pasifik System
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


# =====================================================
# CREATE COMPOUND
# =====================================================

@router.post(
    "/",
    response_model=CompoundResponse,
)
def create_compound(
    compound: CompoundCreate,
    db: Session = Depends(get_db),
):
    new_compound = Compound(
        **compound.dict()
    )

    db.add(new_compound)
    db.commit()
    db.refresh(new_compound)

    return new_compound


# =====================================================
# PAY SINGLE COMPOUND
# =====================================================

@router.post(
    "/pay/{compoundnum}",
    response_model=CompoundResponse,
)
def pay_compound(
    compoundnum: str,
    db: Session = Depends(get_db),
):
    compound = (
        db.query(Compound)
        .filter_by(
            compoundnum=compoundnum
        )
        .first()
    )

    if not compound:
        raise HTTPException(
            status_code=404,
            detail=(
                "Kompaun tidak dijumpai / "
                "Compound not found"
            ),
        )

    if (
        compound.status
        == StatusTypeEnum.paid
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Kompaun telah dibayar / "
                "Compound already paid"
            ),
        )

    compound.status = (
        StatusTypeEnum.paid
    )

    db.commit()
    db.refresh(compound)

    return compound


# =====================================================
# GET ALL COMPOUNDS
# =====================================================

@router.get(
    "/",
    response_model=list[CompoundResponse],
)
def get_compounds(
    db: Session = Depends(get_db),
):
    return db.query(Compound).all()


# =====================================================
# SINGLE COMPOUND RECEIPT QR
# =====================================================

@router.post("/receipt/qr/single")
def view_compound_receipt(
    body: CompoundCreate,
):
    if not body.compoundnum:
        raise HTTPException(
            status_code=400,
            detail=(
                "Nombor kompaun diperlukan / "
                "Compound number required"
            ),
        )

    compound_name = safe_html(body.name)
    compound_no = safe_html(body.compoundnum)
    compound_plate = safe_html(body.plate)
    compound_date = format_date(body.date)
    compound_time = format_time(body.time)
    compound_offense = safe_html(body.offense)
    compound_amount = safe_amount(body.amount)

    pdf_url = generate_single_compound_pdf(
        body
    )

    receipt_html = (
        build_single_compound_html(
            compound_name=compound_name,
            compound_no=compound_no,
            compound_plate=compound_plate,
            compound_date=compound_date,
            compound_time=compound_time,
            compound_offense=compound_offense,
            compound_amount=compound_amount,
            pdf_url=pdf_url,
        )
    )

    html_filename = (
        f"compound_{compound_no}.html"
    )

    html_url = upload_to_blob(
        html_filename,
        receipt_html.encode("utf-8"),
        content_type="text/html",
    )

    return generate_qr_response(
        html_url
    )


# =====================================================
# GET UNPAID COMPOUNDS BY PLATE
# =====================================================

@router.get(
    "/unpaid/{plate}",
    response_model=list[CompoundResponse],
)
def get_unpaid_compounds_by_plate(
    plate: str,
    db: Session = Depends(get_db),
):
    compounds = (
        db.query(Compound)
        .filter(
            Compound.plate == plate,
            Compound.status
            == StatusTypeEnum.unpaid,
        )
        .all()
    )

    if not compounds:
        raise HTTPException(
            status_code=404,
            detail=(
                "Tiada kompaun belum dibayar dijumpai "
                "untuk nombor plat ini / "
                "No unpaid compounds found for this plate"
            ),
        )

    return compounds


# =====================================================
# PAY MULTIPLE COMPOUNDS
# =====================================================

@router.post(
    "/multi/pay",
    response_model=list[MultiCompoundResponse],
)
def pay_multiple_compounds(
    payload: list[MultiCompoundCreate],
    db: Session = Depends(get_db),
):
    if not payload:
        raise HTTPException(
            status_code=400,
            detail=(
                "Tiada kompaun diberikan / "
                "No compounds provided"
            ),
        )

    transaction_id = (
        payload[0].transaction_bank_id
    )

    saved_entries = []

    for item in payload:
        if (
            item.transaction_bank_id
            != transaction_id
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Semua kompaun mesti menggunakan "
                    "ID transaksi bank yang sama / "
                    "All compounds must use the same "
                    "bank transaction ID"
                ),
            )

        compound = (
            db.query(Compound)
            .filter_by(
                compoundnum=item.compoundnum
            )
            .first()
        )

        if not compound:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Kompaun {item.compoundnum} "
                    "tidak dijumpai / "
                    f"Compound {item.compoundnum} "
                    "not found"
                ),
            )

        if (
            compound.status
            == StatusTypeEnum.paid
        ):
            continue

        compound.status = (
            StatusTypeEnum.paid
        )

        db.add(compound)

        record = MultiCompound(
            transaction_bank_id=(
                transaction_id
            ),
            compoundnum=(
                item.compoundnum
            ),
        )

        db.add(record)
        saved_entries.append(record)

    if not saved_entries:
        raise HTTPException(
            status_code=400,
            detail=(
                "Semua kompaun yang dipilih telah dibayar / "
                "All selected compounds have already been paid"
            ),
        )

    db.commit()

    for record in saved_entries:
        db.refresh(record)

    return saved_entries


# =====================================================
# GET COMPOUNDS BY BANK TRANSACTION
# =====================================================

@router.get(
    "/multi/{transaction_bank_id}",
    response_model=list[MultiCompoundResponse],
)
def get_compounds_by_transaction(
    transaction_bank_id: str,
    db: Session = Depends(get_db),
):
    results = (
        db.query(MultiCompound)
        .filter_by(
            transaction_bank_id=(
                transaction_bank_id
            )
        )
        .all()
    )

    if not results:
        raise HTTPException(
            status_code=404,
            detail=(
                "Tiada kompaun dijumpai untuk transaksi ini / "
                "No compounds found for this transaction"
            ),
        )

    return results


# =====================================================
# UPDATE MULTIPLE COMPOUNDS TO PAID
# =====================================================

@router.put("/multi/update")
def update_multiple_compounds_to_paid(
    data: dict,
    db: Session = Depends(get_db),
):
    compound_numbers = data.get(
        "compound_numbers"
    )

    if (
        not compound_numbers
        or not isinstance(
            compound_numbers,
            list,
        )
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "compound_numbers mesti dalam bentuk senarai / "
                "compound_numbers must be a list"
            ),
        )

    updated = []
    skipped = []

    for compound_number in compound_numbers:
        compound = (
            db.query(Compound)
            .filter_by(
                compoundnum=(
                    compound_number
                )
            )
            .first()
        )

        if not compound:
            skipped.append(
                {
                    "compoundnum": (
                        compound_number
                    ),
                    "reason": (
                        "Tidak dijumpai / "
                        "Not found"
                    ),
                }
            )
            continue

        if (
            compound.status
            == StatusTypeEnum.paid
        ):
            skipped.append(
                {
                    "compoundnum": (
                        compound_number
                    ),
                    "reason": (
                        "Telah dibayar / "
                        "Already paid"
                    ),
                }
            )
            continue

        compound.status = (
            StatusTypeEnum.paid
        )

        db.add(compound)

        updated.append(
            compound_number
        )

    db.commit()

    return {
        "message": (
            f"{len(updated)} kompaun dikemas kini "
            "kepada DIBAYAR / "
            f"{len(updated)} compounds updated to PAID"
        ),
        "updated_compounds": updated,
        "skipped": skipped,
    }


# =====================================================
# MULTIPLE COMPOUND RECEIPT QR
# =====================================================

@router.post("/receipt/qr/multi")
def generate_multi_compound_receipt(
    payload: dict,
):
    compounds = payload.get(
        "compounds",
        [],
    )

    total_amount = safe_amount(
        payload.get(
            "total_amount",
            0.0,
        )
    )

    if not compounds:
        raise HTTPException(
            status_code=400,
            detail=(
                "Tiada kompaun diberikan / "
                "No compounds provided"
            ),
        )

    pdf_buffer = generate_multi_compound_pdf(
        compounds,
        total_amount,
    )

    pdf_filename = (
        "multi_compound_receipt.pdf"
    )

    pdf_url = upload_to_blob(
        pdf_filename,
        pdf_buffer.getvalue(),
        content_type="application/pdf",
    )

    receipt_html = (
        build_multi_compound_html(
            compounds=compounds,
            total_amount=total_amount,
            pdf_url=pdf_url,
        )
    )

    html_filename = (
        "multi_compound_receipt.html"
    )

    html_url = upload_to_blob(
        html_filename,
        receipt_html.encode("utf-8"),
        content_type="text/html",
    )

    return generate_qr_response(
        html_url
    )