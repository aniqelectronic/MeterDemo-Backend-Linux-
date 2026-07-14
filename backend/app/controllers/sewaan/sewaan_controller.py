from datetime import datetime
from io import BytesIO
import html

import qrcode
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.controllers.sewaan.sewaan_receipt_bentong import (
    generate_sewaan_receipt_bentong,
)
from app.db.database import get_db
from app.schema.sewaan.sewaan_schema import (
    PaymentUpdatesSewaanBentong,
)
from app.utils.blob_upload import upload_to_blob


router = APIRouter(
    prefix="/sewaan",
    tags=["Sewaan"],
)


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


def _safe(value):
    value = str(value or "").strip()
    return html.escape(value) if value else "-"


def _parse_paid_date(value):
    if not value:
        return datetime.now()

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=(
                "Format paid_date tidak sah / "
                "Invalid paid_date format"
            ),
        )


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


# =========================================================
# HTML RECEIPT
# MALAY BOLD / ENGLISH ITALIC
# =========================================================

def generate_sewaan_receipt_bentong_html(
    paid_date: datetime,
    payment_method: str,
    sewaan_items: list,
    pdf_url: str,
    order_no: str = None,
    bank_trx_no: str = None,
):
    rows_html = ""
    total_amount = 0.0

    for index, item in enumerate(
        sewaan_items,
        start=1,
    ):
        amount = _safe_float(
            item.get("amount")
        )

        total_amount += amount

        rows_html += f"""
        <tr>
            <td class="number-cell">
                {index}
            </td>

            <td>
                {_safe(item.get("account_number"))}
            </td>

            <td>
                {_safe(item.get("tenant_name"))}
            </td>

            <td class="address-cell">
                {_safe(item.get("premise_address"))}
            </td>

            <td>
                {_safe(item.get("start_date"))}
                -
                {_safe(item.get("end_date"))}
            </td>

            <td class="money-cell">
                RM {_format_money(item.get("outstanding_rent"))}
            </td>

            <td class="money-cell">
                RM {_format_money(item.get("current_rent"))}
            </td>

            <td class="money-cell total-paid-cell">
                RM {_format_money(amount)}
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
        Resit Bayaran Sewaan /
        Rental Payment Receipt
    </title>

    <style>
        * {{
            box-sizing: border-box;
        }}

        body {{
            font-family:
                Arial,
                Helvetica,
                sans-serif;
            background: #e8eef8;
            color: #111827;
            padding: 20px;
            margin: 0;
        }}

        .receipt {{
            background: #ffffff;
            max-width: 1050px;
            margin: 0 auto;
            border-radius: 16px;
            overflow: hidden;
            box-shadow:
                0 8px 25px
                rgba(0, 0, 0, 0.10);
        }}

        .header {{
            background: #003b8e;
            color: #ffffff;
            padding: 28px;
            text-align: center;
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
            font-size: 25px;
        }}

        .header .en {{
            color:
                rgba(
                    255,
                    255,
                    255,
                    0.88
                );
            font-size: 15px;
        }}

        .header-address {{
            margin-top: 11px;
            font-size: 13px;
            line-height: 1.5;
            color:
                rgba(
                    255,
                    255,
                    255,
                    0.92
                );
        }}

        .info {{
            padding: 24px 30px;
            background: #f5f9ff;
            border-bottom: 1px solid #d9e8ff;
        }}

        .info-row {{
            display: grid;
            grid-template-columns: 180px 1fr;
            gap: 20px;
            margin-bottom: 14px;
            align-items: start;
        }}

        .info-row:last-child {{
            margin-bottom: 0;
        }}

        .info-label {{
            color: #111827;
        }}

        .info-value {{
            color: #374151;
            word-break: break-word;
        }}

        .table-container {{
            width: 100%;
            overflow-x: auto;
            padding: 26px;
        }}

        table {{
            width: 100%;
            min-width: 950px;
            border-collapse: collapse;
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            overflow: hidden;
        }}

        th {{
            background: #0057d9;
            color: #ffffff;
            padding: 14px 12px;
            text-align: left;
            vertical-align: middle;
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
            padding: 13px 12px;
            border-bottom: 1px solid #e6eefb;
            font-size: 13px;
            vertical-align: top;
        }}

        tbody tr:nth-child(even) {{
            background: #f7fbff;
        }}

        tbody tr:last-child td {{
            border-bottom: none;
        }}

        .number-cell {{
            width: 50px;
            font-weight: 700;
            color: #003b8e;
        }}

        .address-cell {{
            min-width: 220px;
            line-height: 1.45;
        }}

        .money-cell {{
            white-space: nowrap;
            text-align: right;
        }}

        .total-paid-cell {{
            font-weight: 700;
            color: #003b8e;
        }}

        .total {{
            margin: 0 26px 26px;
            background: #003b8e;
            color: #ffffff;
            padding: 18px 22px;
            border-radius: 12px;
            display: flex;
            justify-content: space-between;
            gap: 20px;
            align-items: center;
        }}

        .total .ms,
        .total .en {{
            color: #ffffff;
        }}

        .total-value {{
            font-size: 24px;
            font-weight: 700;
            white-space: nowrap;
        }}

        .button {{
            text-align: center;
            padding: 0 24px 28px;
        }}

        .button a {{
            display: inline-block;
            background: #27ae60;
            color: #ffffff;
            padding: 14px 24px;
            border-radius: 10px;
            text-decoration: none;
        }}

        .button .ms,
        .button .en {{
            color: #ffffff;
        }}

        .note {{
            color: #666666;
            font-size: 12px;
            padding: 0 30px 28px;
            text-align: center;
            line-height: 1.5;
        }}

        .note .ms {{
            color: #4b5563;
        }}

        .note .en {{
            margin-top: 7px;
            color: #6b7280;
        }}

        .footer {{
            background: #f6f8fb;
            text-align: center;
            padding: 22px;
            color: #666666;
            font-size: 13px;
            line-height: 1.5;
        }}

        .footer .ms {{
            color: #003b8e;
        }}

        @media (max-width: 650px) {{
            body {{
                padding: 12px;
            }}

            .header {{
                padding: 24px 16px;
            }}

            .info {{
                padding: 22px 18px;
            }}

            .info-row {{
                display: block;
            }}

            .info-value {{
                margin-top: 5px;
            }}

            .table-container {{
                padding: 18px;
            }}

            .total {{
                display: block;
                text-align: center;
                margin:
                    0 18px 22px;
            }}

            .total-value {{
                margin-top: 10px;
            }}
        }}
    </style>
</head>

<body>
    <div class="receipt">
        <div class="header">
            <div class="ms">
                MAJLIS PERBANDARAN BENTONG
            </div>

            <div class="en">
                BENTONG MUNICIPAL COUNCIL
            </div>

            <div class="header-address">
                Jalan Ketari,
                28700 Bentong,
                Pahang Darul Makmur
            </div>

            <div style="margin-top: 14px;">
                <div class="ms">
                    Resit Bayaran Sewaan
                </div>

                <div class="en">
                    Rental Payment Receipt
                </div>
            </div>
        </div>

        <div class="info">
            <div class="info-row">
                <div class="info-label">
                    <div class="ms">
                        No. Resit
                    </div>

                    <div class="en">
                        Receipt No.
                    </div>
                </div>

                <div class="info-value">
                    {_safe(order_no)}
                </div>
            </div>

            <div class="info-row">
                <div class="info-label">
                    <div class="ms">
                        Tarikh Dibayar
                    </div>

                    <div class="en">
                        Paid Date
                    </div>
                </div>

                <div class="info-value">
                    {paid_date.strftime("%d %b %Y %I:%M %p")}
                </div>
            </div>

            <div class="info-row">
                <div class="info-label">
                    <div class="ms">
                        Kaedah Pembayaran
                    </div>

                    <div class="en">
                        Payment Method
                    </div>
                </div>

                <div class="info-value">
                    {_safe(payment_method)}
                </div>
            </div>

            <div class="info-row">
                <div class="info-label">
                    <div class="ms">
                        No. Transaksi Bank
                    </div>

                    <div class="en">
                        Bank Transaction No.
                    </div>
                </div>

                <div class="info-value">
                    {_safe(bank_trx_no)}
                </div>
            </div>
        </div>

        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>
                            <div class="ms">
                                Bil.
                            </div>

                            <div class="en">
                                No.
                            </div>
                        </th>

                        <th>
                            <div class="ms">
                                No. Akaun
                            </div>

                            <div class="en">
                                Account No.
                            </div>
                        </th>

                        <th>
                            <div class="ms">
                                Nama Penyewa
                            </div>

                            <div class="en">
                                Tenant Name
                            </div>
                        </th>

                        <th>
                            <div class="ms">
                                Alamat Premis
                            </div>

                            <div class="en">
                                Premise Address
                            </div>
                        </th>

                        <th>
                            <div class="ms">
                                Tempoh Sewaan
                            </div>

                            <div class="en">
                                Rental Period
                            </div>
                        </th>

                        <th>
                            <div class="ms">
                                Tunggakan Sewa
                            </div>

                            <div class="en">
                                Outstanding Rent
                            </div>
                        </th>

                        <th>
                            <div class="ms">
                                Sewa Semasa
                            </div>

                            <div class="en">
                                Current Rent
                            </div>
                        </th>

                        <th>
                            <div class="ms">
                                Jumlah Dibayar
                            </div>

                            <div class="en">
                                Amount Paid
                            </div>
                        </th>
                    </tr>
                </thead>

                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>

        <div class="total">
            <div>
                <div class="ms">
                    Jumlah Dibayar
                </div>

                <div class="en">
                    Total Paid
                </div>
            </div>

            <div class="total-value">
                RM {_format_money(total_amount)}
            </div>
        </div>

        <div class="button">
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

        <div class="note">
            <div class="ms">
                Sila maklum bahawa kemas kini baki akaun
                mungkin diproses pada hari bekerja berikutnya.
            </div>

            <div class="en">
                Please be informed that account balance updates
                may be processed on the following working day.
            </div>
        </div>

        <div class="footer">
            <div class="ms">
                Majlis Perbandaran Bentong
            </div>

            <div class="en">
                Bentong Municipal Council
            </div>

            Jalan Ketari,
            28700 Bentong,
            Pahang Darul Makmur

            <br>

            <strong>Telefon:</strong>
            04-5497555
            &nbsp;|&nbsp;
            <strong>Aplikasi:</strong>
            TIP Bentong

            <br>

            <em>
                Telephone: 04-5497555 |
                Application: TIP Bentong
            </em>
        </div>
    </div>
</body>
</html>
"""


# =========================================================
# GENERATE BENTONG SEWAAN RECEIPT QR
# =========================================================

@router.post("/receipt/qr/bentong")
def generate_bentong_sewaan_receipt(
    payload: dict,
):
    order_no = payload.get("order_no")
    paid_date_raw = payload.get("paid_date")
    payment_method = payload.get(
        "payment_method",
        "N/A",
    )
    bank_trx_no = payload.get(
        "bank_trx_no"
    )
    sewaan_items = payload.get(
        "sewaan_items",
        [],
    )

    if not order_no:
        raise HTTPException(
            status_code=400,
            detail=(
                "order_no diperlukan / "
                "Missing order_no"
            ),
        )

    if not sewaan_items:
        raise HTTPException(
            status_code=400,
            detail=(
                "Tiada item sewaan diberikan / "
                "No sewaan items provided"
            ),
        )

    for index, item in enumerate(
        sewaan_items,
        start=1,
    ):
        if not item.get("account_number"):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"account_number tiada pada item {index} / "
                    f"Missing account_number at item {index}"
                ),
            )

        if not item.get("tenant_name"):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"tenant_name tiada pada item {index} / "
                    f"Missing tenant_name at item {index}"
                ),
            )

        if not item.get("premise_address"):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"premise_address tiada pada item {index} / "
                    f"Missing premise_address at item {index}"
                ),
            )

        if item.get("amount") is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"amount tiada pada item {index} / "
                    f"Missing amount at item {index}"
                ),
            )

    paid_date = _parse_paid_date(
        paid_date_raw
    )

    pdf_bytes = generate_sewaan_receipt_bentong(
        paid_date=paid_date,
        payment_method=payment_method,
        sewaan_items=sewaan_items,
        order_no=order_no,
        bank_trx_no=bank_trx_no,
    )

    pdf_filename = (
        f"bentong_sewaan_receipt_{order_no}.pdf"
    )

    pdf_url = upload_to_blob(
        pdf_filename,
        pdf_bytes,
        content_type="application/pdf",
    )

    html_receipt = (
        generate_sewaan_receipt_bentong_html(
            paid_date=paid_date,
            payment_method=payment_method,
            sewaan_items=sewaan_items,
            pdf_url=pdf_url,
            order_no=order_no,
            bank_trx_no=bank_trx_no,
        )
    )

    html_filename = (
        f"bentong_sewaan_receipt_{order_no}.html"
    )

    html_url = upload_to_blob(
        html_filename,
        html_receipt.encode("utf-8"),
        content_type="text/html",
    )

    return _generate_qr_response(
        html_url
    )


# =========================================================
# CREATE SEWAAN PAYMENT UPDATES
# =========================================================

@router.post(
    "/payment-updates-sewaan-bentong"
)
def create_payment_updates_sewaan_bentong(
    payload: dict,
    db: Session = Depends(get_db),
):
    order_no = payload.get("order_no")
    paid_date_raw = payload.get("paid_date")
    payment_method = payload.get(
        "payment_method"
    )
    bank_trx_no = payload.get(
        "bank_trx_no"
    )
    sewaan_items = payload.get(
        "sewaan_items",
        [],
    )

    if not order_no:
        raise HTTPException(
            status_code=400,
            detail=(
                "order_no diperlukan / "
                "Missing order_no"
            ),
        )

    if not paid_date_raw:
        raise HTTPException(
            status_code=400,
            detail=(
                "paid_date diperlukan / "
                "Missing paid_date"
            ),
        )

    if not sewaan_items:
        raise HTTPException(
            status_code=400,
            detail=(
                "Tiada item sewaan diberikan / "
                "No sewaan items provided"
            ),
        )

    paid_date = _parse_paid_date(
        paid_date_raw
    )

    created_updates = []

    for index, item in enumerate(
        sewaan_items,
        start=1,
    ):
        required_fields = [
            "account_number",
            "tenant_name",
            "premise_address",
        ]

        for field_name in required_fields:
            if not item.get(field_name):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"{field_name} tiada pada item {index} / "
                        f"Missing {field_name} at item {index}"
                    ),
                )

        if item.get("amount") is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"amount tiada pada item {index} / "
                    f"Missing amount at item {index}"
                ),
            )

        payment_update = (
            PaymentUpdatesSewaanBentong(
                order_no=order_no,
                no_pendaftaran=(
                    item.get("no_pendaftaran")
                ),
                account_number=(
                    item.get("account_number")
                ),
                tenant_name=(
                    item.get("tenant_name")
                ),
                premise_address=(
                    item.get("premise_address")
                ),
                amount=_safe_float(
                    item.get("amount")
                ),
                payment_method=payment_method,
                bank_trx_no=bank_trx_no,
                paid_date=paid_date,
            )
        )

        db.add(payment_update)
        created_updates.append(
            payment_update
        )

    db.commit()

    for payment_update in created_updates:
        db.refresh(payment_update)

    return {
        "message": (
            "Rekod pembayaran sewaan berjaya dicipta / "
            "Sewaan payment updates created successfully"
        ),
        "total_records": len(created_updates),
        "data": created_updates,
    }


# =========================================================
# SEMAKAN SEWAAN PAYMENT UPDATES
# =========================================================

@router.get(
    "/payment-updates-sewaan-bentong/semakan"
)
def semakan_payment_updates_sewaan_bentong(
    no_pendaftaran: str = None,
    account_number: str = None,
    order_no: str = None,
    db: Session = Depends(get_db),
):
    if (
        not no_pendaftaran
        and not account_number
        and not order_no
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Sila berikan no_pendaftaran, "
                "account_number atau order_no / "
                "Please provide no_pendaftaran, "
                "account_number or order_no"
            ),
        )

    query = db.query(
        PaymentUpdatesSewaanBentong
    )

    if order_no:
        query = query.filter(
            PaymentUpdatesSewaanBentong
            .order_no
            == order_no
        )

    elif account_number:
        query = query.filter(
            PaymentUpdatesSewaanBentong
            .account_number
            == account_number
        )

    elif no_pendaftaran:
        query = query.filter(
            PaymentUpdatesSewaanBentong
            .no_pendaftaran
            == no_pendaftaran
        )

    results = query.order_by(
        PaymentUpdatesSewaanBentong
        .paid_date
        .desc()
    ).all()

    if not results:
        raise HTTPException(
            status_code=404,
            detail=(
                "Tiada rekod pembayaran sewaan dijumpai / "
                "No sewaan payment update found"
            ),
        )

    return results