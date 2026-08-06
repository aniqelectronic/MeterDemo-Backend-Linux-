from datetime import datetime
from io import BytesIO
import html

import qrcode
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.controllers.v2.bill.bill_receipt import (
    generate_bill_receipt,
)
from app.utils.blob_upload import upload_to_blob


router = APIRouter(
    prefix="/bill",
    tags=["Bill Receipt V2"],
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
    clean_value = str(value or "").strip()
    return html.escape(clean_value) if clean_value else "-"


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


def _validate_payload(payload):
    required_fields = [
        "order_no",
        "bill_type",
        "bill_code",
        "account_number",
        "bill_amount",
        "total_amount",
    ]

    missing_fields = []

    for field_name in required_fields:
        value = payload.get(field_name)

        if value is None or str(value).strip() == "":
            missing_fields.append(field_name)

    if missing_fields:
        joined_fields = ", ".join(missing_fields)

        raise HTTPException(
            status_code=400,
            detail=(
                f"Medan diperlukan tiada: {joined_fields} / "
                f"Missing required fields: {joined_fields}"
            ),
        )

    bill_amount = _safe_float(payload.get("bill_amount"))
    total_amount = _safe_float(payload.get("total_amount"))

    if bill_amount <= 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "bill_amount mesti melebihi 0 / "
                "bill_amount must be greater than 0"
            ),
        )

    if total_amount <= 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "total_amount mesti melebihi 0 / "
                "total_amount must be greater than 0"
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

def generate_bill_receipt_html(
    paid_date: datetime,
    payment_method: str,
    bill_type: str,
    bill_code: str,
    account_number: str,
    bill_amount: float,
    total_amount: float,
    pdf_url: str,
    order_no: str = None,
    bank_trx_no: str = None,
):
    return f"""
<!DOCTYPE html>
<html lang="ms">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="color-scheme" content="only light">

    <title>Resit Bayaran Bil / Bill Payment Receipt</title>

    <style>
        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            padding: 22px;
            background: #eaf1fa;
            color: #172033;
            font-family: Arial, Helvetica, sans-serif;
        }}

        .receipt {{
            max-width: 820px;
            margin: 0 auto;
            overflow: hidden;
            background: #ffffff;
            border-radius: 18px;
            box-shadow: 0 12px 34px rgba(18, 59, 112, 0.16);
        }}

        .header {{
            padding: 30px 26px;
            color: #ffffff;
            text-align: center;
            background: linear-gradient(135deg, #123b70, #1976d2, #42a5f5);
        }}

        .ms {{
            font-weight: 700;
        }}

        .en {{
            margin-top: 4px;
            color: #6b7280;
            font-size: 0.88em;
            font-style: italic;
            font-weight: 400;
        }}

        .header .ms,
        .header .en {{
            color: #ffffff;
        }}

        .header-title .ms {{
            font-size: 27px;
        }}

        .header-title .en {{
            color: rgba(255, 255, 255, 0.88);
            font-size: 15px;
        }}

        .header-address {{
            margin-top: 10px;
            color: rgba(255, 255, 255, 0.92);
            font-size: 13px;
            line-height: 1.55;
        }}

        .receipt-title {{
            margin-top: 17px;
        }}

        .receipt-title .ms {{
            font-size: 21px;
        }}

        .receipt-title .en {{
            color: rgba(255, 255, 255, 0.88);
            font-size: 14px;
        }}

        .success-strip {{
            display: flex;
            gap: 16px;
            align-items: center;
            margin: 24px 26px 0;
            padding: 18px 20px;
            background: #edf9f2;
            border: 1px solid #a8ddbc;
            border-radius: 14px;
        }}

        .success-icon {{
            display: flex;
            width: 52px;
            height: 52px;
            flex: 0 0 52px;
            align-items: center;
            justify-content: center;
            color: #ffffff;
            background: #17935f;
            border-radius: 50%;
            font-size: 28px;
            font-weight: 700;
        }}

        .success-text .ms {{
            color: #087443;
            font-size: 18px;
        }}

        .success-text .en {{
            color: #3f6b57;
            font-size: 13px;
        }}

        .section {{
            padding: 26px;
        }}

        .section-title {{
            margin-bottom: 14px;
            color: #123b70;
            font-size: 18px;
        }}

        .details {{
            overflow: hidden;
            border: 1px solid #d5e3f2;
            border-radius: 14px;
        }}

        .detail-row {{
            display: grid;
            grid-template-columns: 210px 1fr;
            gap: 22px;
            align-items: center;
            padding: 16px 18px;
            border-bottom: 1px solid #e3edf7;
        }}

        .detail-row:nth-child(odd) {{
            background: #f6f9fd;
        }}

        .detail-row:last-child {{
            border-bottom: 0;
        }}

        .detail-label {{
            color: #243447;
        }}

        .detail-value {{
            color: #172033;
            font-size: 15px;
            font-weight: 700;
            overflow-wrap: anywhere;
        }}

        .amount-card {{
            display: flex;
            gap: 20px;
            align-items: center;
            justify-content: space-between;
            margin: 0 26px 24px;
            padding: 22px 24px;
            color: #ffffff;
            background: linear-gradient(135deg, #123b70, #286da8);
            border-radius: 14px;
            box-shadow: 0 8px 18px rgba(18, 59, 112, 0.20);
        }}

        .amount-card .ms,
        .amount-card .en {{
            color: #ffffff;
        }}

        .amount-value {{
            white-space: nowrap;
            font-size: 28px;
            font-weight: 800;
        }}

        .download {{
            padding: 0 26px 24px;
            text-align: center;
        }}

        .download a {{
            display: inline-block;
            min-width: 240px;
            padding: 14px 24px;
            color: #ffffff;
            background: #17935f;
            border-radius: 10px;
            text-decoration: none;
            box-shadow: 0 6px 14px rgba(23, 147, 95, 0.20);
        }}

        .download a .ms,
        .download a .en {{
            color: #ffffff;
        }}

        .note {{
            margin: 0 26px 26px;
            padding: 16px 18px;
            color: #5c6672;
            background: #fff9e9;
            border: 1px solid #ead39a;
            border-radius: 12px;
            text-align: center;
            font-size: 12px;
            line-height: 1.55;
        }}

        .note .ms {{
            color: #705616;
        }}

        .note .en {{
            color: #7a6a42;
        }}

        .footer {{
            padding: 22px;
            color: #66717e;
            background: #f5f7fa;
            border-top: 1px solid #e2e8f0;
            text-align: center;
            font-size: 13px;
            line-height: 1.55;
        }}

        .footer .ms {{
            color: #123b70;
        }}

        @media (max-width: 650px) {{
            body {{
                padding: 12px;
            }}

            .header {{
                padding: 24px 16px;
            }}

            .success-strip,
            .amount-card,
            .note {{
                margin-left: 16px;
                margin-right: 16px;
            }}

            .section {{
                padding: 20px 16px;
            }}

            .detail-row {{
                display: block;
            }}

            .detail-value {{
                margin-top: 7px;
            }}

            .amount-card {{
                display: block;
                text-align: center;
            }}

            .amount-value {{
                margin-top: 12px;
            }}
        }}
    </style>
</head>

<body>
    <div class="receipt">
        <div class="header">
            <div class="header-title">
                <div class="ms">TIP Digital Kiosk</div>
                <div class="en">Digital Self-Service Kiosk</div>
            </div>


            <div class="receipt-title">
                <div class="ms">Resit Bayaran Bil</div>
                <div class="en">Bill Payment Receipt</div>
            </div>
        </div>

        <div class="success-strip">
            <div class="success-icon">&#10003;</div>
            <div class="success-text">
                <div class="ms">Pembayaran berjaya</div>
                <div class="en">Payment successful</div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">
                <div class="ms">Butiran Transaksi</div>
                <div class="en">Transaction Details</div>
            </div>

            <div class="details">
                <div class="detail-row">
                    <div class="detail-label">
                        <div class="ms">No. Resit</div>
                        <div class="en">Receipt No.</div>
                    </div>
                    <div class="detail-value">{_safe(order_no)}</div>
                </div>

                <div class="detail-row">
                    <div class="detail-label">
                        <div class="ms">Tarikh Dibayar</div>
                        <div class="en">Paid Date</div>
                    </div>
                    <div class="detail-value">
                        {paid_date.strftime("%d %b %Y %I:%M %p")}
                    </div>
                </div>

                <div class="detail-row">
                    <div class="detail-label">
                        <div class="ms">Kaedah Pembayaran</div>
                        <div class="en">Payment Method</div>
                    </div>
                    <div class="detail-value">{_safe(payment_method)}</div>
                </div>

                <div class="detail-row">
                    <div class="detail-label">
                        <div class="ms">No. Transaksi Bank</div>
                        <div class="en">Bank Transaction No.</div>
                    </div>
                    <div class="detail-value">{_safe(bank_trx_no)}</div>
                </div>
            </div>
        </div>

        <div class="section" style="padding-top: 0;">
            <div class="section-title">
                <div class="ms">Butiran Bayaran Bil</div>
                <div class="en">Bill Payment Details</div>
            </div>

            <div class="details">
                <div class="detail-row">
                    <div class="detail-label">
                        <div class="ms">Jenis / Penyedia Bil</div>
                        <div class="en">Bill Type / Provider</div>
                    </div>
                    <div class="detail-value">{_safe(bill_type)}</div>
                </div>

                <div class="detail-row">
                    <div class="detail-label">
                        <div class="ms">Kod Bil</div>
                        <div class="en">Bill Code</div>
                    </div>
                    <div class="detail-value">{_safe(bill_code)}</div>
                </div>

                <div class="detail-row">
                    <div class="detail-label">
                        <div class="ms">Nombor Akaun</div>
                        <div class="en">Account Number</div>
                    </div>
                    <div class="detail-value">{_safe(account_number)}</div>
                </div>

                <div class="detail-row">
                    <div class="detail-label">
                        <div class="ms">Amaun Bil</div>
                        <div class="en">Bill Amount</div>
                    </div>
                    <div class="detail-value">
                        RM {_format_money(bill_amount)}
                    </div>
                </div>
            </div>
        </div>

        <div class="amount-card">
            <div>
                <div class="ms">Jumlah Dibayar</div>
                <div class="en">Total Paid</div>
            </div>
            <div class="amount-value">
                RM {_format_money(total_amount)}
            </div>
        </div>

        <div class="download">
            <a href="{pdf_url}" target="_blank" rel="noopener">
                <div class="ms">Muat Turun Resit PDF</div>
                <div class="en">Download PDF Receipt</div>
            </a>
        </div>

        <div class="note">
            <div class="ms">
                Simpan resit ini sebagai bukti pembayaran. Kemas kini akaun bil
                tertakluk kepada tempoh pemprosesan penyedia bil.
            </div>
            <div class="en">
                Please retain this receipt as proof of payment. Bill account
                updates are subject to the provider's processing time.
            </div>
        </div>

        <div class="footer">
            <div class="ms">
                TIP Digital Kiosk
            </div>

            <div class="en">
                Digital Self-Service Kiosk
            </div>

            <br>

            <div class="ms">
                Resit ini dijana secara elektronik dan
                tidak memerlukan tandatangan.
            </div>

            <div class="en">
                This receipt is electronically generated
                and requires no signature.
            </div>
        </div>
    </div>
</body>
</html>
"""


# =========================================================
# GENERATE BILL RECEIPT QR
# =========================================================

@router.post("/receipt/qr")
def generate_bill_receipt(payload: dict):
    _validate_payload(payload)

    order_no = str(payload.get("order_no")).strip()
    paid_date = _parse_paid_date(payload.get("paid_date"))
    payment_method = payload.get("payment_method", "DuitNow QR")
    bank_trx_no = payload.get("bank_trx_no")
    bill_type = payload.get("bill_type")
    bill_code = payload.get("bill_code")
    account_number = payload.get("account_number")
    bill_amount = _safe_float(payload.get("bill_amount"))
    total_amount = _safe_float(payload.get("total_amount"))

    pdf_bytes = generate_bill_receipt(
        paid_date=paid_date,
        payment_method=payment_method,
        bill_type=bill_type,
        bill_code=bill_code,
        account_number=account_number,
        bill_amount=bill_amount,
        total_amount=total_amount,
        order_no=order_no,
        bank_trx_no=bank_trx_no,
    )

    safe_order_no = "".join(
        character
        if character.isalnum() or character in ("-", "_")
        else "_"
        for character in order_no
    )

    pdf_filename = f"bill_receipt_{safe_order_no}.pdf"

    pdf_url = upload_to_blob(
        pdf_filename,
        pdf_bytes,
        content_type="application/pdf",
    )

    html_receipt = generate_bill_receipt_html(
        paid_date=paid_date,
        payment_method=payment_method,
        bill_type=bill_type,
        bill_code=bill_code,
        account_number=account_number,
        bill_amount=bill_amount,
        total_amount=total_amount,
        pdf_url=pdf_url,
        order_no=order_no,
        bank_trx_no=bank_trx_no,
    )

    html_filename = f"bill_receipt_{safe_order_no}.html"

    html_url = upload_to_blob(
        html_filename,
        html_receipt.encode("utf-8"),
        content_type="text/html",
    )

    return _generate_qr_response(html_url)