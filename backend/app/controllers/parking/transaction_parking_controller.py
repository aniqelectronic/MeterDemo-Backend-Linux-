# app/controllers/transaction_parking_controller.py

from io import BytesIO
import html

import qrcode
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.controllers.parking.parking_receipt import generate_parking_receipt
from app.db.database import get_db
from app.models.parking.transaction_parking_model import TransactionResponse
from app.schema.parking.parking_schema import Parking
from app.schema.parking.transaction_parking_schema import TransactionParking
from app.utils.blob_upload import upload_to_blob


router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"],
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


def _format_datetime(value):
    if not value:
        return "-"

    try:
        return value.strftime("%d/%m/%Y %I:%M %p")
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
    image.save(buffer, format="PNG")
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="image/png",
    )


def _generate_parking_receipt_html(
    ticket_id,
    plate,
    hours,
    time_in,
    time_out,
    amount,
    transaction_type,
    order_no,
    bank_trx_no,
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
        E-Resit Parkir /
        Parking E-Receipt
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
            min-height: 100vh;
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
            background:
                linear-gradient(
                    135deg,
                    #003b8e,
                    #0a66d8
                );
            color: #ffffff;
            padding: 34px 30px;
            text-align: center;
        }}

        .header::after {{
            content: "";
            position: absolute;
            width: 220px;
            height: 220px;
            border-radius: 50%;
            background:
                rgba(255, 255, 255, 0.08);
            right: -70px;
            top: -90px;
        }}

        .brand {{
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

        .brand-title .ms {{
            font-size: 30px;
            line-height: 1.1;
        }}

        .brand-title .en {{
            font-size: 17px;
            margin-top: 7px;
        }}

        .issued-by {{
            margin-top: 15px;
            font-size: 13px;
            line-height: 1.45;
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
            background: #f8fbff;
            border: 1px solid #dce8f8;
            border-radius: 14px;
            padding: 16px;
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
            word-break: break-word;
        }}

        .amount-card {{
            margin-top: 22px;
            padding: 20px 22px;
            border-radius: 16px;
            background:
                linear-gradient(
                    135deg,
                    #eaf3ff,
                    #f5f9ff
                );
            border-left: 6px solid #0a66d8;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 20px;
        }}

        .amount-label .ms {{
            color: #0f3f83;
            font-size: 17px;
        }}

        .amount-label .en {{
            font-size: 13px;
        }}

        .amount-value {{
            font-size: 30px;
            font-weight: 800;
            color: #0a56c2;
            white-space: nowrap;
        }}

        .status-note {{
            margin-top: 28px;
            text-align: center;
            color: #15803d;
        }}

        .status-note .ms {{
            font-size: 19px;
        }}

        .status-note .en {{
            color: #2f855a;
            font-size: 14px;
        }}

        .download-btn {{
            text-align: center;
            margin-top: 28px;
        }}

        .download-btn a {{
            display: inline-block;
            min-width: 250px;
            padding: 14px 24px;
            background:
                linear-gradient(
                    135deg,
                    #16a34a,
                    #22c55e
                );
            color: #ffffff;
            text-decoration: none;
            border-radius: 12px;
            box-shadow:
                0 8px 18px
                rgba(34, 197, 94, 0.25);
            transition:
                transform 0.2s ease,
                box-shadow 0.2s ease;
        }}

        .download-btn a:hover {{
            transform: translateY(-1px);
            box-shadow:
                0 10px 24px
                rgba(34, 197, 94, 0.32);
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

            .brand-title .ms {{
                font-size: 24px;
            }}

            .brand-title .en {{
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

        @media print {{
            body {{
                background: #ffffff;
                padding: 0;
            }}

            .receipt {{
                border: none;
                box-shadow: none;
                border-radius: 0;
            }}

            .download-btn {{
                display: none;
            }}
        }}
    </style>
</head>

<body>
    <div class="page">
        <div class="receipt">
            <div class="header">
                <div class="brand">
                    <div class="brand-title">
                        <div class="ms">
                            E-Resit Parkir
                        </div>

                        <div class="en">
                            Parking E-Receipt
                        </div>
                    </div>

                    <div class="issued-by">
                        <div class="ms">
                            Dikeluarkan oleh
                            Juara Inovasi Pasifik
                        </div>

                        <div class="en">
                            Issued by
                            Juara Inovasi Pasifik
                        </div>
                    </div>
                </div>
            </div>

            <div class="content">
                <div class="summary-grid">
                    <div class="summary-card">
                        <div class="label">
                            <div class="ms">
                                ID Tiket
                            </div>

                            <div class="en">
                                Ticket ID
                            </div>
                        </div>

                        <div class="value">
                            {_safe_html(ticket_id)}
                        </div>
                    </div>

                    <div class="summary-card">
                        <div class="label">
                            <div class="ms">
                                Nombor Plat
                            </div>

                            <div class="en">
                                Plate Number
                            </div>
                        </div>

                        <div class="value">
                            {_safe_html(plate)}
                        </div>
                    </div>

                    <div class="summary-card">
                        <div class="label">
                            <div class="ms">
                                Tempoh
                            </div>

                            <div class="en">
                                Duration
                            </div>
                        </div>

                        <div class="value">
                            {_safe_html(hours)} jam
                        </div>
                    </div>

                    <div class="summary-card">
                        <div class="label">
                            <div class="ms">
                                Jenis Transaksi
                            </div>

                            <div class="en">
                                Transaction Type
                            </div>
                        </div>

                        <div class="value">
                            {_safe_html(transaction_type)}
                        </div>
                    </div>

                    <div class="summary-card">
                        <div class="label">
                            <div class="ms">
                                Waktu Mula
                            </div>

                            <div class="en">
                                Time In
                            </div>
                        </div>

                        <div class="value">
                            {_format_datetime(time_in)}
                        </div>
                    </div>

                    <div class="summary-card">
                        <div class="label">
                            <div class="ms">
                                Waktu Tamat
                            </div>

                            <div class="en">
                                Time Out
                            </div>
                        </div>

                        <div class="value">
                            {_format_datetime(time_out)}
                        </div>
                    </div>

                    <div class="summary-card">
                        <div class="label">
                            <div class="ms">
                                No. Pesanan
                            </div>

                            <div class="en">
                                Order No.
                            </div>
                        </div>

                        <div class="value">
                            {_safe_html(order_no)}
                        </div>
                    </div>

                    <div class="summary-card">
                        <div class="label">
                            <div class="ms">
                                No. Transaksi Bank
                            </div>

                            <div class="en">
                                Bank Transaction No.
                            </div>
                        </div>

                        <div class="value">
                            {_safe_html(bank_trx_no)}
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
                        RM {_safe_amount(amount):,.2f}
                    </div>
                </div>

                <div class="status-note">
                    <div class="ms">
                        Terima kasih!
                        Pandu dengan selamat.
                    </div>

                    <div class="en">
                        Thank you!
                        Drive safely.
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


def _build_receipt_qr(transaction, parking):
    pdf_bytes = generate_parking_receipt(
        ticket_id=transaction.ticket_id,
        plate=transaction.plate,
        hours=transaction.hours,
        time_in=(
            parking.timein
            if parking
            else "N/A"
        ),
        time_out=(
            parking.timeout
            if parking
            else "N/A"
        ),
        amount=transaction.amount,
        transaction_type=(
            transaction.transaction_type
            if transaction
            else "N/A"
        ),
        order_no=transaction.order_no,
        bank_trx_no=transaction.bank_trx_no,
    )

    pdf_filename = (
        f"receipt_{transaction.ticket_id}.pdf"
    )

    pdf_url = upload_to_blob(
        pdf_filename,
        pdf_bytes,
        content_type="application/pdf",
    )

    receipt_html = _generate_parking_receipt_html(
        ticket_id=transaction.ticket_id,
        plate=transaction.plate,
        hours=transaction.hours,
        time_in=(
            parking.timein
            if parking
            else None
        ),
        time_out=(
            parking.timeout
            if parking
            else None
        ),
        amount=transaction.amount,
        transaction_type=(
            transaction.transaction_type
            if transaction
            else "N/A"
        ),
        order_no=transaction.order_no,
        bank_trx_no=transaction.bank_trx_no,
        pdf_url=pdf_url,
    )

    html_filename = (
        f"receipt_{transaction.ticket_id}.html"
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
# GET ALL TRANSACTIONS
# =========================================================

@router.get(
    "/",
    response_model=list[TransactionResponse],
)
def get_all_transactions(
    db: Session = Depends(get_db),
):
    transactions = (
        db.query(TransactionParking)
        .all()
    )

    return transactions or []


# =========================================================
# RECEIPT QR BY TICKET
# =========================================================

@router.get(
    "/receipt/view/{ticket_id}",
    response_class=HTMLResponse,
)
def view_receipt(
    ticket_id: str,
    db: Session = Depends(get_db),
):
    transaction = (
        db.query(TransactionParking)
        .filter(
            TransactionParking.ticket_id
            == ticket_id
        )
        .first()
    )

    if not transaction:
        raise HTTPException(
            status_code=404,
            detail=(
                "Tiket tidak dijumpai / "
                "Ticket not found"
            ),
        )

    parking = (
        db.query(Parking)
        .filter(
            Parking.plate
            == transaction.plate
        )
        .order_by(Parking.id.desc())
        .first()
    )

    db.expunge_all()
    db.close()

    return _build_receipt_qr(
        transaction,
        parking,
    )


# =========================================================
# GET TRANSACTION BY TICKET
# =========================================================

@router.get(
    "/{ticket_id}",
    response_model=TransactionResponse,
)
def get_transaction_by_ticket(
    ticket_id: str,
    db: Session = Depends(get_db),
):
    transaction = (
        db.query(TransactionParking)
        .filter(
            TransactionParking.ticket_id
            == ticket_id
        )
        .first()
    )

    if not transaction:
        raise HTTPException(
            status_code=404,
            detail=(
                "Transaksi tidak dijumpai / "
                "Transaction not found"
            ),
        )

    return transaction


# =========================================================
# GET LATEST RECEIPT QR
# =========================================================

@router.get("/latest/qr")
def get_latest_qr(
    db: Session = Depends(get_db),
):
    transaction = (
        db.query(TransactionParking)
        .order_by(
            TransactionParking.id.desc()
        )
        .first()
    )

    if not transaction:
        raise HTTPException(
            status_code=404,
            detail=(
                "Tiada transaksi dijumpai / "
                "No transactions found"
            ),
        )

    parking = (
        db.query(Parking)
        .filter(
            Parking.plate
            == transaction.plate
        )
        .order_by(Parking.id.desc())
        .first()
    )

    db.expunge_all()
    db.close()

    return _build_receipt_qr(
        transaction,
        parking,
    )


# =========================================================
# LATEST RECEIPT BY PLATE
# =========================================================

@router.get("/latest/{plate}")
def get_latest_receipt_by_plate(
    plate: str,
    db: Session = Depends(get_db),
):
    transaction = (
        db.query(TransactionParking)
        .filter(
            TransactionParking.plate
            == plate
        )
        .order_by(
            TransactionParking.id.desc()
        )
        .first()
    )

    if not transaction:
        raise HTTPException(
            status_code=404,
            detail=(
                "Tiada transaksi dijumpai untuk "
                "nombor plat ini / "
                "No transaction found for this plate"
            ),
        )

    parking = (
        db.query(Parking)
        .filter(Parking.plate == plate)
        .order_by(Parking.id.desc())
        .first()
    )

    return {
        "ticket_id": transaction.ticket_id,
        "terminal": transaction.terminal,
        "plate": transaction.plate,
        "hours": transaction.hours,
        "amount": transaction.amount,
        "transaction_type": (
            transaction.transaction_type
        ),
        "order_no": transaction.order_no,
        "bank_trx_no": (
            transaction.bank_trx_no
        ),
        "time_in": (
            parking.timein
            if parking
            else None
        ),
        "time_out": (
            parking.timeout
            if parking
            else None
        ),
    }