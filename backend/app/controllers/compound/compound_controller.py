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


router = APIRouter(prefix="/compound", tags=["Compound"])


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def safe_html(value, fallback="-"):
    """
    Convert a value to escaped HTML text.
    This prevents special characters from breaking the receipt HTML.
    """
    if value is None:
        return fallback

    text = str(value).strip()
    if not text:
        return fallback

    return html.escape(text)


def safe_amount(value):
    """
    Convert an amount safely to float.
    """
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def format_date(value):
    """
    Format a date as DD/MM/YYYY when possible.
    """
    if value is None:
        return "-"

    try:
        return value.strftime("%d/%m/%Y")
    except (AttributeError, ValueError):
        return safe_html(value)


def format_time(value):
    """
    Format a time as 12-hour time with AM/PM when possible.
    """
    if value is None:
        return "-"

    try:
        return value.strftime("%I:%M %p")
    except (AttributeError, ValueError):
        return safe_html(value)


def generate_qr_response(receipt_url: str):
    """
    Generate a QR PNG response pointing to the uploaded HTML receipt.
    """
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


# =====================================================
# CREATE COMPOUND
# =====================================================

@router.post("/", response_model=CompoundResponse)
def create_compound(
    compound: CompoundCreate,
    db: Session = Depends(get_db),
):
    """
    Dummy testing payload example:

    {
        "compoundnum": "MBMBCMP2025000123",
        "plate": "ABC1234",
        "date": "2025-09-22",
        "time": "15:45:00",
        "offense": "Illegal Parking",
        "amount": 50.0
    }
    """

    new_compound = Compound(**compound.dict())

    db.add(new_compound)
    db.commit()
    db.refresh(new_compound)

    return new_compound


# =====================================================
# PAY SINGLE COMPOUND
# =====================================================

@router.post("/pay/{compoundnum}", response_model=CompoundResponse)
def pay_compound(
    compoundnum: str,
    db: Session = Depends(get_db),
):
    compound = (
        db.query(Compound)
        .filter_by(compoundnum=compoundnum)
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

    if compound.status == StatusTypeEnum.paid:
        raise HTTPException(
            status_code=400,
            detail=(
                "Kompaun telah dibayar / "
                "Compound already paid"
            ),
        )

    compound.status = StatusTypeEnum.paid

    db.commit()
    db.refresh(compound)

    return compound


# =====================================================
# GET ALL COMPOUNDS
# =====================================================

@router.get("/", response_model=list[CompoundResponse])
def get_compounds(db: Session = Depends(get_db)):
    return db.query(Compound).all()


# =====================================================
# SINGLE COMPOUND RECEIPT QR
# =====================================================

@router.post("/receipt/qr/single")
def view_compound_receipt(body: CompoundCreate):
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

    # Generate bilingual PDF from compound_receipt.py
    pdf_url = generate_single_compound_pdf(body)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ms">
    <head>
        <meta charset="utf-8">
        <meta
            name="viewport"
            content="width=device-width, initial-scale=1"
        >
        <meta name="color-scheme" content="only light">

        <title>E-Resit Kompaun / Compound E-Receipt</title>

        <style>
            * {{
                box-sizing: border-box;
            }}

            body {{
                font-family: "Segoe UI", Tahoma, Arial, sans-serif;
                background: #eceff1;
                color: #111827;
                margin: 0;
                padding: 25px;
                display: flex;
                justify-content: center;
            }}

            .receipt {{
                background: #ffffff;
                border-radius: 16px;
                padding: 30px 35px;
                width: 100%;
                max-width: 700px;
                box-shadow: 0 6px 18px rgba(0, 0, 0, 0.08);
            }}

            .header {{
                background: #2f80ed;
                color: #ffffff;
                padding: 22px;
                border-radius: 12px;
                text-align: center;
            }}

            .header h1 {{
                margin: 0;
                font-size: 27px;
            }}

            .header p {{
                margin: 8px 0 0;
                font-size: 15px;
                opacity: 0.95;
            }}

            .info-section {{
                margin-top: 25px;
                font-size: 17px;
                background: #f9fbff;
                border: 1px solid #e1e8f5;
                border-radius: 12px;
                padding: 8px 20px;
            }}

            .info-row {{
                display: flex;
                justify-content: space-between;
                gap: 20px;
                padding: 12px 0;
                border-bottom: 1px dashed #d8dee9;
            }}

            .info-row:last-child {{
                border-bottom: none;
            }}

            .info-label {{
                font-weight: 700;
                text-align: left;
            }}

            .info-value {{
                text-align: right;
                word-break: break-word;
            }}

            .amount-box {{
                margin-top: 25px;
                padding: 18px;
                background: #f4f7ff;
                border-left: 6px solid #2f80ed;
                border-radius: 10px;
                font-size: 20px;
                font-weight: 700;
                color: #111827;
                text-align: right;
            }}

            .amount-box span {{
                color: #1d4ed8;
                font-size: 25px;
            }}

            .thankyou {{
                margin-top: 30px;
                font-size: 18px;
                font-weight: 700;
                color: #15803d;
                text-align: center;
                line-height: 1.5;
            }}

            .download-btn {{
                margin-top: 30px;
                text-align: center;
            }}

            .download-btn a {{
                display: inline-block;
                background: #27ae60;
                padding: 13px 25px;
                font-size: 17px;
                font-weight: 600;
                color: #ffffff;
                border-radius: 10px;
                text-decoration: none;
            }}

            .footer {{
                margin-top: 28px;
                text-align: center;
                font-size: 13px;
                color: #6b7280;
            }}

            @media (max-width: 600px) {{
                body {{
                    padding: 12px;
                }}

                .receipt {{
                    padding: 22px 18px;
                }}

                .header h1 {{
                    font-size: 22px;
                }}

                .info-row {{
                    display: block;
                }}

                .info-value {{
                    margin-top: 5px;
                    text-align: left;
                }}

                .amount-box {{
                    text-align: center;
                }}
            }}
        </style>
    </head>

    <body>
        <div class="receipt">
            <div class="header">
                <h1>E-Resit Kompaun / Compound E-Receipt</h1>
                <p>
                    Rekod Transaksi Rasmi /
                    Official Transaction Record
                </p>
            </div>

            <div class="info-section">
                <div class="info-row">
                    <span class="info-label">
                        Nama / Name
                    </span>
                    <span class="info-value">
                        {compound_name}
                    </span>
                </div>

                <div class="info-row">
                    <span class="info-label">
                        No. Kompaun / Compound No.
                    </span>
                    <span class="info-value">
                        {compound_no}
                    </span>
                </div>

                <div class="info-row">
                    <span class="info-label">
                        No. Plat / Plate No.
                    </span>
                    <span class="info-value">
                        {compound_plate}
                    </span>
                </div>

                <div class="info-row">
                    <span class="info-label">
                        Tarikh / Date
                    </span>
                    <span class="info-value">
                        {compound_date}
                    </span>
                </div>

                <div class="info-row">
                    <span class="info-label">
                        Masa / Time
                    </span>
                    <span class="info-value">
                        {compound_time}
                    </span>
                </div>

                <div class="info-row">
                    <span class="info-label">
                        Kesalahan / Offense
                    </span>
                    <span class="info-value">
                        {compound_offense}
                    </span>
                </div>
            </div>

            <div class="amount-box">
                Jumlah Dibayar / Total Paid:
                <span>RM {compound_amount:.2f}</span>
            </div>

            <div class="thankyou">
                Terima kasih atas pembayaran anda.<br>
                Thank you for your payment.
            </div>

            <div class="download-btn">
                <a href="{pdf_url}" target="_blank">
                    Muat Turun Resit PDF /
                    Download PDF Receipt
                </a>
            </div>

            <div class="footer">
                &copy; 2025 City Car Park System &bull;
                Hak Cipta Terpelihara /
                All Rights Reserved
            </div>
        </div>
    </body>
    </html>
    """

    html_bytes = html_content.encode("utf-8")
    html_filename = f"compound_{compound_no}.html"

    html_url = upload_to_blob(
        html_filename,
        html_bytes,
        content_type="text/html",
    )

    return generate_qr_response(html_url)


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
            Compound.status == StatusTypeEnum.unpaid,
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
    """
    Example payload:

    [
        {
            "transaction_bank_id": "BANKTXN123456",
            "compoundnum": "MBMBCMP2025000123"
        },
        {
            "transaction_bank_id": "BANKTXN123456",
            "compoundnum": "MBMBCMP2025000456"
        }
    ]
    """

    if not payload:
        raise HTTPException(
            status_code=400,
            detail=(
                "Tiada kompaun diberikan / "
                "No compounds provided"
            ),
        )

    transaction_id = payload[0].transaction_bank_id
    saved_entries = []

    for item in payload:
        if item.transaction_bank_id != transaction_id:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Semua kompaun mesti menggunakan ID transaksi "
                    "bank yang sama / "
                    "All compounds must use the same bank transaction ID"
                ),
            )

        compound = (
            db.query(Compound)
            .filter_by(compoundnum=item.compoundnum)
            .first()
        )

        if not compound:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Kompaun {item.compoundnum} tidak dijumpai / "
                    f"Compound {item.compoundnum} not found"
                ),
            )

        # Skip records that are already paid
        if compound.status == StatusTypeEnum.paid:
            continue

        compound.status = StatusTypeEnum.paid
        db.add(compound)

        record = MultiCompound(
            transaction_bank_id=transaction_id,
            compoundnum=item.compoundnum,
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
        .filter_by(transaction_bank_id=transaction_bank_id)
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
    """
    Example payload:

    {
        "compound_numbers": [
            "MBPPCMP20252",
            "MBPPCMP20253"
        ]
    }
    """

    compound_numbers = data.get("compound_numbers")

    if (
        not compound_numbers
        or not isinstance(compound_numbers, list)
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
            .filter_by(compoundnum=compound_number)
            .first()
        )

        if not compound:
            skipped.append(
                {
                    "compoundnum": compound_number,
                    "reason": "Tidak dijumpai / Not found",
                }
            )
            continue

        if compound.status == StatusTypeEnum.paid:
            skipped.append(
                {
                    "compoundnum": compound_number,
                    "reason": "Telah dibayar / Already paid",
                }
            )
            continue

        compound.status = StatusTypeEnum.paid

        db.add(compound)
        updated.append(compound_number)

    db.commit()

    return {
        "message": (
            f"{len(updated)} kompaun dikemas kini kepada DIBAYAR / "
            f"{len(updated)} compounds updated to PAID"
        ),
        "updated_compounds": updated,
        "skipped": skipped,
    }


# =====================================================
# MULTIPLE COMPOUND RECEIPT QR
# =====================================================

@router.post("/receipt/qr/multi")
def generate_multi_compound_receipt(payload: dict):
    """
    Example payload:

    {
        "compounds": [
            {
                "compoundnum": "MBMBCMP2025000123",
                "amount": 50.0
            },
            {
                "compoundnum": "MBMBCMP2025000456",
                "amount": 70.0
            }
        ],
        "total_amount": 120.0
    }
    """

    compounds = payload.get("compounds", [])
    total_amount = safe_amount(
        payload.get("total_amount", 0.0)
    )

    if not compounds:
        raise HTTPException(
            status_code=400,
            detail=(
                "Tiada kompaun diberikan / "
                "No compounds provided"
            ),
        )

    # Generate bilingual PDF from compound_receipt.py
    pdf_buffer = generate_multi_compound_pdf(
        compounds,
        total_amount,
    )

    pdf_filename = "multi_compound_receipt.pdf"

    pdf_url = upload_to_blob(
        pdf_filename,
        pdf_buffer.getvalue(),
        content_type="application/pdf",
    )

    rows_html = ""

    for compound in compounds:
        compound_number = safe_html(
            compound.get("compoundnum")
        )

        amount = safe_amount(
            compound.get("amount", 0)
        )

        rows_html += f"""
            <tr>
                <td>{compound_number}</td>
                <td>RM {amount:.2f}</td>
            </tr>
        """

    html_content = f"""
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

            body {{
                font-family: "Segoe UI", Tahoma, Arial, sans-serif;
                background: #e8ebef;
                color: #111827;
                padding: 25px;
                margin: 0;
            }}

            .receipt {{
                background: #ffffff;
                padding: 35px;
                width: 100%;
                max-width: 800px;
                border-radius: 16px;
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
                margin: 0 auto;
                height: auto !important;
                overflow: visible !important;
            }}

            .header {{
                background: #2f80ed;
                color: #ffffff;
                padding: 22px 18px;
                text-align: center;
                border-radius: 12px;
            }}

            .header h1 {{
                margin: 0;
                font-size: 27px;
            }}

            .header p {{
                margin: 8px 0 0;
                font-size: 15px;
                opacity: 0.95;
            }}

            .table-container {{
                width: 100%;
                overflow-x: auto;
                margin-top: 25px;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
            }}

            table {{
                width: 100%;
                min-width: 550px;
                border-collapse: collapse;
                page-break-inside: auto;
            }}

            th {{
                background: #f5f8ff;
                padding: 13px 12px;
                border-bottom: 2px solid #d9e2f2;
                font-size: 16px;
                font-weight: 700;
                text-align: center;
            }}

            th small {{
                display: block;
                margin-top: 4px;
                color: #4b5563;
                font-size: 12px;
                font-weight: 500;
            }}

            td {{
                padding: 13px 12px;
                text-align: center;
                border-bottom: 1px solid #eeeeee;
                font-size: 16px;
            }}

            tbody tr:nth-child(even) {{
                background: #fafafa;
            }}

            tbody tr:last-child td {{
                border-bottom: none;
            }}

            .total {{
                margin-top: 22px;
                background: #f4f7ff;
                padding: 17px;
                font-size: 20px;
                font-weight: 700;
                border-left: 6px solid #2f80ed;
                border-radius: 10px;
                text-align: right;
            }}

            .total span {{
                color: #1d4ed8;
                font-size: 24px;
            }}

            .thankyou {{
                margin-top: 30px;
                color: #15803d;
                text-align: center;
                font-size: 18px;
                font-weight: 700;
                line-height: 1.5;
            }}

            .pdf-button {{
                margin-top: 27px;
                text-align: center;
            }}

            .pdf-button a {{
                display: inline-block;
                background: #27ae60;
                padding: 13px 22px;
                color: #ffffff;
                text-decoration: none;
                font-size: 17px;
                border-radius: 10px;
                font-weight: 600;
            }}

            .footer {{
                margin-top: 28px;
                text-align: center;
                font-size: 13px;
                color: #6b7280;
            }}

            @media (max-width: 600px) {{
                body {{
                    padding: 12px;
                }}

                .receipt {{
                    padding: 20px 15px;
                }}

                .header h1 {{
                    font-size: 22px;
                }}

                .total {{
                    text-align: center;
                }}
            }}
        </style>
    </head>

    <body>
        <div class="receipt">
            <div class="header">
                <h1>
                    Resit Pelbagai Kompaun /
                    Multiple Compound Receipt
                </h1>

                <p>
                    Rekod Transaksi Rasmi /
                    Official Transaction Record
                </p>
            </div>

            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>
                                No. Kompaun
                                <small>Compound Number</small>
                            </th>

                            <th>
                                Jumlah (RM)
                                <small>Amount (RM)</small>
                            </th>
                        </tr>
                    </thead>

                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>

            <div class="total">
                Jumlah Keseluruhan / Total Amount:
                <span>RM {total_amount:.2f}</span>
            </div>

            <div class="thankyou">
                Terima kasih atas pembayaran anda.<br>
                Thank you for your payment.
            </div>

            <div class="pdf-button">
                <a href="{pdf_url}" target="_blank">
                    Muat Turun Resit PDF /
                    Download PDF Receipt
                </a>
            </div>

            <div class="footer">
                &copy; 2025 City Car Park System &bull;
                Hak Cipta Terpelihara /
                All Rights Reserved
            </div>
        </div>
    </body>
    </html>
    """

    html_bytes = html_content.encode("utf-8")
    html_filename = "multi_compound_receipt.html"

    html_url = upload_to_blob(
        html_filename,
        html_bytes,
        content_type="text/html",
    )

    return generate_qr_response(html_url)