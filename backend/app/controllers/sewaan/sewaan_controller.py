from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse
from datetime import datetime
from io import BytesIO
import qrcode
from app.utils.blob_upload import upload_to_blob 
from app.schema.sewaan.sewaan_schema import PaymentUpdatesSewaanBentong

# Import your sewaan receipt generator
from app.controllers.sewaan.sewaan_receipt_bentong import generate_sewaan_receipt_bentong
from app.db.database import get_db


router = APIRouter(prefix="/sewaan", tags=["Sewaan"])


def _format_money(value):
    try:
        return f"{float(value):,.2f}"
    except Exception:
        return "0.00"


def _safe(value):
    value = str(value or "").strip()
    return value if value else "-"


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

    for index, item in enumerate(sewaan_items, start=1):
        amount = float(item.get("amount", 0) or 0)
        total_amount += amount

        rows_html += f"""
        <tr>
            <td>{index}</td>
            <td>{_safe(item.get("account_number"))}</td>
            <td>{_safe(item.get("tenant_name"))}</td>
            <td>{_safe(item.get("premise_address"))}</td>
            <td>{_safe(item.get("start_date"))} - {_safe(item.get("end_date"))}</td>
            <td>RM {_format_money(item.get("outstanding_rent"))}</td>
            <td>RM {_format_money(item.get("current_rent"))}</td>
            <td><b>RM {_format_money(amount)}</b></td>
        </tr>
        """

    return f"""
    <html>
    <head>
        <title>Resit Sewaan / Sewaan Receipt</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #e8eef8;
                padding: 20px;
                margin: 0;
            }}
            .receipt {{
                background: white;
                max-width: 950px;
                margin: 0 auto;
                border-radius: 16px;
                overflow: hidden;
                box-shadow: 0 8px 25px rgba(0,0,0,0.10);
            }}
            .header {{
                background: #003B8E;
                color: white;
                padding: 24px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
            }}
            .header p {{
                margin: 6px 0 0;
                font-size: 14px;
            }}
            .info {{
                padding: 22px 28px;
                background: #f5f9ff;
                border-bottom: 1px solid #d9e8ff;
            }}
            .info div {{
                margin-bottom: 7px;
                font-size: 15px;
            }}
            .table-container {{
                overflow-x: auto;
                padding: 24px;
            }}
            table {{
                width: 100%;
                min-width: 850px;
                border-collapse: collapse;
            }}
            th {{
                background: #0057D9;
                color: white;
                padding: 12px;
                font-size: 12px;
                text-align: left;
                line-height: 1.4;
            }}
            td {{
                padding: 11px;
                border-bottom: 1px solid #e6eefb;
                font-size: 13px;
                vertical-align: top;
            }}
            tr:nth-child(even) {{
                background: #f7fbff;
            }}
            .total {{
                margin: 0 24px 24px;
                background: #003B8E;
                color: white;
                padding: 16px 20px;
                border-radius: 12px;
                font-size: 20px;
                font-weight: bold;
                text-align: right;
            }}
            .button {{
                text-align: center;
                padding: 0 24px 28px;
            }}
            .button a {{
                background: #0057D9;
                color: white;
                padding: 13px 22px;
                border-radius: 10px;
                text-decoration: none;
                font-weight: bold;
                display: inline-block;
            }}
            .note {{
                color: #666;
                font-size: 12px;
                padding: 0 28px 24px;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="receipt">
            <div class="header">
                <h1>MAJLIS PERBANDARAN BENTONG</h1>
                <p>Resit Bayaran Sewaan / Rental Payment Receipt</p>
            </div>

            <div class="info">
                <div><b>No. Resit / Receipt No:</b> {order_no or "-"}</div>
                <div><b>Tarikh Dibayar / Paid Date:</b> {paid_date.strftime("%d %b %Y %I:%M %p")}</div>
                <div><b>Kaedah Pembayaran / Payment Method:</b> {_safe(payment_method)}</div>
                <div><b>No. Transaksi Bank / Bank Transaction No:</b> {bank_trx_no or "-"}</div>
            </div>

            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>No. Akaun<br>Account No</th>
                            <th>Nama Penyewa<br>Tenant Name</th>
                            <th>Alamat Premis<br>Premise Address</th>
                            <th>Tempoh Sewaan<br>Rental Period</th>
                            <th>Tunggakan Sewa<br>Outstanding Rent</th>
                            <th>Sewa Semasa<br>Current Rent</th>
                            <th>Jumlah Dibayar<br>Amount Paid</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>

            <div class="total">
                Jumlah Dibayar / Total Paid: RM {_format_money(total_amount)}
            </div>

            <div class="button">
                <a href="{pdf_url}" target="_blank">Muat Turun Resit PDF / Download PDF Receipt</a>
            </div>

            <div class="note">
                Sila maklum bahawa kemas kini baki akaun mungkin diproses pada hari bekerja berikutnya. /
                Please be informed that account balance updates may be processed on the following working day.
            </div>
        </div>
    </body>
    </html>
    """


@router.post("/receipt/qr/bentong")
def generate_bentong_sewaan_receipt(payload: dict):
    order_no = payload.get("order_no")
    paid_date_raw = payload.get("paid_date")
    payment_method = payload.get("payment_method", "N/A")
    bank_trx_no = payload.get("bank_trx_no")
    sewaan_items = payload.get("sewaan_items", [])

    if not order_no:
        raise HTTPException(status_code=400, detail="Missing order_no")

    if not sewaan_items:
        raise HTTPException(status_code=400, detail="No sewaan items provided")

    for index, item in enumerate(sewaan_items, start=1):
        if not item.get("account_number"):
            raise HTTPException(
                status_code=400,
                detail=f"Missing account_number at item {index}",
            )

        if not item.get("tenant_name"):
            raise HTTPException(
                status_code=400,
                detail=f"Missing tenant_name at item {index}",
            )

        if not item.get("premise_address"):
            raise HTTPException(
                status_code=400,
                detail=f"Missing premise_address at item {index}",
            )

        if item.get("amount") is None:
            raise HTTPException(
                status_code=400,
                detail=f"Missing amount at item {index}",
            )

    if paid_date_raw:
        paid_date = datetime.fromisoformat(paid_date_raw)
    else:
        paid_date = datetime.now()

    pdf_bytes = generate_sewaan_receipt_bentong(
        paid_date=paid_date,
        payment_method=payment_method,
        sewaan_items=sewaan_items,
        order_no=order_no,
        bank_trx_no=bank_trx_no,
    )

    pdf_filename = f"bentong_sewaan_receipt_{order_no}.pdf"

    pdf_url = upload_to_blob(
        pdf_filename,
        pdf_bytes,
        content_type="application/pdf",
    )

    html_receipt = generate_sewaan_receipt_bentong_html(
        paid_date=paid_date,
        payment_method=payment_method,
        sewaan_items=sewaan_items,
        pdf_url=pdf_url,
        order_no=order_no,
        bank_trx_no=bank_trx_no,
    )

    html_filename = f"bentong_sewaan_receipt_{order_no}.html"

    html_url = upload_to_blob(
        html_filename,
        html_receipt.encode("utf-8"),
        content_type="text/html",
    )

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
    )

    qr.add_data(html_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buf = BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")


@router.post("/payment-updates-sewaan-bentong")
def create_payment_updates_sewaan_bentong(
    payload: dict,
    db: Session = Depends(get_db)
):
    order_no = payload.get("order_no")
    paid_date_raw = payload.get("paid_date")
    payment_method = payload.get("payment_method")
    bank_trx_no = payload.get("bank_trx_no")
    sewaan_items = payload.get("sewaan_items", [])

    if not order_no:
        raise HTTPException(status_code=400, detail="Missing order_no")

    if not paid_date_raw:
        raise HTTPException(status_code=400, detail="Missing paid_date")

    if not sewaan_items:
        raise HTTPException(status_code=400, detail="No sewaan items provided")

    try:
        paid_date = datetime.fromisoformat(paid_date_raw)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid paid_date format")

    created_updates = []

    for index, item in enumerate(sewaan_items, start=1):
        if not item.get("account_number"):
            raise HTTPException(
                status_code=400,
                detail=f"Missing account_number at item {index}"
            )

        if not item.get("tenant_name"):
            raise HTTPException(
                status_code=400,
                detail=f"Missing tenant_name at item {index}"
            )

        if not item.get("premise_address"):
            raise HTTPException(
                status_code=400,
                detail=f"Missing premise_address at item {index}"
            )

        if item.get("amount") is None:
            raise HTTPException(
                status_code=400,
                detail=f"Missing amount at item {index}"
            )

        payment_update = PaymentUpdatesSewaanBentong(
            order_no=order_no,
            no_pendaftaran=item.get("no_pendaftaran"),
            account_number=item.get("account_number"),
            tenant_name=item.get("tenant_name"),
            premise_address=item.get("premise_address"),
            amount=float(item.get("amount")),
            payment_method=payment_method,
            bank_trx_no=bank_trx_no,
            paid_date=paid_date
        )

        db.add(payment_update)
        created_updates.append(payment_update)

    db.commit()

    for payment_update in created_updates:
        db.refresh(payment_update)

    return {
        "message": "Sewaan payment updates created successfully",
        "total_records": len(created_updates),
        "data": created_updates
    }
    
    
@router.get("/payment-updates-sewaan-bentong/semakan")
def semakan_payment_updates_sewaan_bentong(
    no_pendaftaran: str = None,
    account_number: str = None,
    order_no: str = None,
    db: Session = Depends(get_db)
):
    if not no_pendaftaran and not account_number and not order_no:
        raise HTTPException(
            status_code=400,
            detail="Please provide no_pendaftaran, account_number or order_no"
        )

    query = db.query(PaymentUpdatesSewaanBentong)

    if order_no:
        query = query.filter(
            PaymentUpdatesSewaanBentong.order_no == order_no
        )

    elif account_number:
        query = query.filter(
            PaymentUpdatesSewaanBentong.account_number == account_number
        )

    elif no_pendaftaran:
        query = query.filter(
            PaymentUpdatesSewaanBentong.no_pendaftaran == no_pendaftaran
        )

    results = query.order_by(
        PaymentUpdatesSewaanBentong.paid_date.desc()
    ).all()

    if not results:
        raise HTTPException(
            status_code=404,
            detail="No sewaan payment update found"
        )

    return results