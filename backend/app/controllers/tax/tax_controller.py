from datetime import datetime, timedelta
from io import BytesIO
from typing import List
import html

import qrcode
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.controllers.tax.tax_receipt import generate_multi_tax_pdf
from app.controllers.tax.tax_receipt_bentong import generate_tax_receipt_bentong
from app.db.database import get_db
from app.models.tax.tax_model import (
    OwnerCreate,
    PropertyCreate,
    TaxCreate,
    TaxResponse,
)
from app.schema.tax.tax_schema import (
    CukaiTaksiran,
    Owner,
    PaymentUpdatesCukaiTaksiranBentong,
    Property,
)
from app.utils.blob_upload import upload_to_blob


router = APIRouter(
    prefix="/tax",
    tags=["Cukai Taksiran"],
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


def _safe_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


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
# OWNER
# =========================================================

@router.post("/owner", response_model=OwnerCreate)
def create_owner(
    owner: OwnerCreate,
    db: Session = Depends(get_db),
):
    new_owner = Owner(**owner.dict())

    db.add(new_owner)
    db.commit()
    db.refresh(new_owner)

    return new_owner


# =========================================================
# PROPERTY
# =========================================================

@router.post("/property", response_model=PropertyCreate)
def create_property(
    prop: PropertyCreate,
    db: Session = Depends(get_db),
):
    new_property = Property(**prop.dict())

    db.add(new_property)
    db.commit()
    db.refresh(new_property)

    return new_property


# =========================================================
# CREATE MULTIPLE TAXES
# =========================================================

@router.post("/", response_model=List[TaxResponse])
def create_multiple_taxes(
    taxes: List[TaxCreate],
    db: Session = Depends(get_db),
):
    created_taxes = []

    for tax in taxes:
        owner = (
            db.query(Owner)
            .filter(Owner.id == tax.owner_id)
            .first()
        )

        if not owner:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"ID pemilik {tax.owner_id} tidak dijumpai / "
                    f"Owner ID {tax.owner_id} not found"
                ),
            )

        tax_data = tax.dict()
        tax_data["owner_name"] = owner.name

        new_tax = CukaiTaksiran(**tax_data)

        if new_tax.issue_date:
            new_tax.issue_date += timedelta(hours=8)

        if new_tax.due_date:
            new_tax.due_date += timedelta(hours=8)

        db.add(new_tax)
        db.commit()
        db.refresh(new_tax)

        created_taxes.append(new_tax)

    return created_taxes


# =========================================================
# GET ALL TAXES
# =========================================================

@router.get("/", response_model=List[TaxResponse])
def get_taxes(db: Session = Depends(get_db)):
    return db.query(CukaiTaksiran).all()


# =========================================================
# GET SINGLE TAX BY BILL NUMBER
# =========================================================

@router.get("/{bill_no}", response_model=TaxResponse)
def get_tax(
    bill_no: str,
    db: Session = Depends(get_db),
):
    tax = (
        db.query(CukaiTaksiran)
        .filter(CukaiTaksiran.bill_no == bill_no)
        .first()
    )

    if not tax:
        raise HTTPException(
            status_code=404,
            detail=(
                "Cukai tidak dijumpai / "
                "Tax not found"
            ),
        )

    result = tax.__dict__.copy()

    result["property_type"] = (
        tax.property.property_type
        if tax.property
        else None
    )

    return result


# =========================================================
# GET TAXES BY OWNER IC
# =========================================================

@router.get("/by-ic/{ic}")
def get_taxes_by_ic_with_property_type(
    ic: str,
    db: Session = Depends(get_db),
):
    owner = (
        db.query(Owner)
        .filter(Owner.ic == ic)
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

    taxes = (
        db.query(CukaiTaksiran)
        .filter(CukaiTaksiran.owner_id == owner.id)
        .all()
    )

    if not taxes:
        raise HTTPException(
            status_code=404,
            detail=(
                "Tiada cukai dijumpai untuk pemilik ini / "
                "No taxes found for this owner"
            ),
        )

    result = []

    for tax in taxes:
        tax_dict = tax.__dict__.copy()

        tax_dict["property_type"] = (
            tax.property.property_type
            if tax.property
            else None
        )

        result.append(tax_dict)

    return result


# =========================================================
# RENEW TAX
# TESTING / DEMO ONLY
# =========================================================

@router.post(
    "/renew/{bill_no}",
    response_model=TaxResponse,
)
def renew_tax(
    bill_no: str,
    db: Session = Depends(get_db),
    extra_days: int = 180,
):
    tax = (
        db.query(CukaiTaksiran)
        .filter(CukaiTaksiran.bill_no == bill_no)
        .first()
    )

    if not tax:
        raise HTTPException(
            status_code=404,
            detail=(
                "Bil cukai tidak dijumpai / "
                "Tax bill not found"
            ),
        )

    tax.due_date += timedelta(days=extra_days)

    db.add(tax)
    db.commit()
    db.refresh(tax)

    return tax


# =========================================================
# BENTONG TAX HTML RECEIPT
# MALAY BOLD / ENGLISH ITALIC
# =========================================================

def generate_tax_receipt_bentong_html(
    paid_date: datetime,
    payment_method: str,
    tax_items: list,
    pdf_url: str,
    order_no: str,
    bank_trx_no: str = None,
):
    total_amount = sum(
        _safe_float(item.get("amount"))
        for item in tax_items
    )

    rows_html = ""

    for index, item in enumerate(
        tax_items,
        start=1,
    ):
        account_number = _safe_html(
            item.get("account_number")
        )

        owner_name = _safe_html(
            item.get("owner_name")
        )

        property_address = _safe_html(
            item.get("property_address")
        )

        amount = _safe_float(
            item.get("amount")
        )

        rows_html += f"""
        <tr>
            <td class="number-cell">{index}</td>

            <td class="item-cell">
                <div class="item-title">
                    <div class="ms">Cukai Taksiran</div>
                    <div class="en">Assessment Tax</div>
                </div>

                <div class="field">
                    <div class="field-label">
                        <div class="ms">Nombor Akaun</div>
                        <div class="en">Account Number</div>
                    </div>

                    <div class="field-value">
                        {account_number}
                    </div>
                </div>

                <div class="field">
                    <div class="field-label">
                        <div class="ms">Nama Pemilik</div>
                        <div class="en">Owner Name</div>
                    </div>

                    <div class="field-value">
                        {owner_name}
                    </div>
                </div>

                <div class="field address-field">
                    <div class="field-label">
                        <div class="ms">Alamat Harta</div>
                        <div class="en">Property Address</div>
                    </div>

                    <div class="field-value address">
                        {property_address}
                    </div>
                </div>
            </td>

            <td class="amount-cell">
                RM {amount:,.2f}
            </td>
        </tr>
        """

    bank_html = ""

    if bank_trx_no:
        bank_html = f"""
        <div class="meta-row">
            <div class="meta-label">
                <div class="ms">No. Transaksi Bank</div>
                <div class="en">Bank Transaction No.</div>
            </div>

            <div class="meta-value">
                {_safe_html(bank_trx_no)}
            </div>
        </div>
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
        Resit Cukai Taksiran /
        Assessment Tax Receipt
    </title>

    <style>
        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            padding: 30px;
            background: #eef3f8;
            font-family: Arial, Helvetica, sans-serif;
            color: #222222;
        }}

        .receipt {{
            max-width: 880px;
            margin: auto;
            background: #ffffff;
            border-radius: 18px;
            overflow: hidden;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.10);
        }}

        .header {{
            background:
                linear-gradient(
                    135deg,
                    #12a8e0,
                    #083b73
                );
            color: #ffffff;
            padding: 30px 40px;
            text-align: center;
        }}

        .header .ms {{
            color: #ffffff;
        }}

        .header .en {{
            color: rgba(255, 255, 255, 0.88);
        }}

        .council-title {{
            font-size: 23px;
            margin-bottom: 6px;
        }}

        .header-address {{
            margin-top: 10px;
            font-size: 13px;
            line-height: 1.5;
        }}

        .content {{
            padding: 35px 40px;
        }}

        .ms {{
            font-weight: 700;
        }}

        .en {{
            margin-top: 2px;
            font-style: italic;
            font-weight: 400;
            color: #6b7280;
            font-size: 0.88em;
        }}

        .title-row {{
            display: flex;
            justify-content: space-between;
            gap: 30px;
            border-bottom: 1px solid #e5e7eb;
            padding-bottom: 24px;
            flex-wrap: wrap;
        }}

        .receipt-title .ms {{
            color: #083b73;
            font-size: 34px;
            line-height: 1;
        }}

        .receipt-title .en {{
            color: #2f80ed;
            font-size: 18px;
            margin-top: 6px;
        }}

        .receipt-no {{
            color: #4b5563;
            font-weight: 700;
            margin-top: 12px;
        }}

        .meta {{
            min-width: 300px;
        }}

        .meta-row {{
            display: grid;
            grid-template-columns: 150px 1fr;
            gap: 18px;
            margin-bottom: 13px;
            align-items: start;
        }}

        .meta-label {{
            color: #111827;
        }}

        .meta-value {{
            color: #374151;
            word-break: break-word;
        }}

        .table-container {{
            width: 100%;
            overflow-x: auto;
            margin-top: 30px;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
        }}

        table {{
            width: 100%;
            min-width: 720px;
            border-collapse: collapse;
        }}

        th {{
            background: #083b73;
            color: #ffffff;
            padding: 14px 13px;
            text-align: left;
            vertical-align: middle;
        }}

        th .ms {{
            color: #ffffff;
        }}

        th .en {{
            color: rgba(255, 255, 255, 0.85);
        }}

        td {{
            padding: 18px 13px;
            border-bottom: 1px solid #eeeeee;
            vertical-align: top;
            font-size: 14px;
        }}

        tbody tr:nth-child(even) {{
            background: #f8fbff;
        }}

        tbody tr:last-child td {{
            border-bottom: none;
        }}

        .number-cell {{
            width: 55px;
            font-weight: 700;
            color: #083b73;
        }}

        .item-cell {{
            min-width: 440px;
        }}

        .item-title {{
            margin-bottom: 14px;
        }}

        .item-title .ms {{
            color: #083b73;
            font-size: 16px;
        }}

        .item-title .en {{
            font-size: 13px;
        }}

        .field {{
            display: grid;
            grid-template-columns: 160px 1fr;
            gap: 18px;
            margin-top: 10px;
            align-items: start;
        }}

        .field-label {{
            color: #111827;
        }}

        .field-value {{
            color: #374151;
            line-height: 1.45;
            word-break: break-word;
        }}

        .address {{
            color: #4b5563;
        }}

        .amount-cell {{
            width: 145px;
            text-align: right;
            white-space: nowrap;
            font-weight: 700;
            color: #083b73;
        }}

        .total {{
            background: #083b73;
            color: #ffffff;
            margin-top: 25px;
            padding: 18px 20px;
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

        .note {{
            text-align: center;
            color: #666666;
            font-size: 12px;
            margin-top: 27px;
            line-height: 1.5;
            padding: 0 20px;
        }}

        .note .ms {{
            color: #4b5563;
        }}

        .note .en {{
            margin-top: 7px;
            color: #6b7280;
        }}

        .download {{
            text-align: center;
            margin-top: 30px;
        }}

        .download a {{
            display: inline-block;
            background: #27ae60;
            color: #ffffff;
            padding: 14px 26px;
            border-radius: 12px;
            text-decoration: none;
            font-size: 17px;
        }}

        .download a .ms,
        .download a .en {{
            color: #ffffff;
        }}

        .footer {{
            background: #f6f8fb;
            text-align: center;
            padding: 24px;
            color: #666666;
            font-size: 13px;
            line-height: 1.5;
        }}

        .footer .ms {{
            color: #083b73;
        }}

        .footer .en {{
            margin-bottom: 8px;
        }}

        @media (max-width: 650px) {{
            body {{
                padding: 12px;
            }}

            .header {{
                padding: 25px 18px;
            }}

            .content {{
                padding: 25px 18px;
            }}

            .meta {{
                min-width: 100%;
            }}

            .meta-row {{
                display: block;
            }}

            .meta-value {{
                margin-top: 5px;
            }}

            .total {{
                display: block;
                text-align: center;
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
            <div class="council-title">
                <div class="ms">
                    Majlis Perbandaran Bentong
                </div>

                <div class="en">
                    Bentong Municipal Council
                </div>
            </div>

            <div class="header-address">
                Jalan Ketari,
                28700 Bentong,
                Pahang Darul Makmur
            </div>
        </div>

        <div class="content">
            <div class="title-row">
                <div class="receipt-title">
                    <div class="ms">Resit</div>
                    <div class="en">Receipt</div>

                    <div class="receipt-no">
                        #{_safe_html(order_no)}
                    </div>
                </div>

                <div class="meta">
                    <div class="meta-row">
                        <div class="meta-label">
                            <div class="ms">
                                Dibayar pada
                            </div>

                            <div class="en">
                                Paid at
                            </div>
                        </div>

                        <div class="meta-value">
                            {paid_date.strftime("%d %b %Y")}
                        </div>
                    </div>

                    <div class="meta-row">
                        <div class="meta-label">
                            <div class="ms">
                                Kaedah Pembayaran
                            </div>

                            <div class="en">
                                Payment Method
                            </div>
                        </div>

                        <div class="meta-value">
                            {_safe_html(payment_method)}
                        </div>
                    </div>

                    {bank_html}
                </div>
            </div>

            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>
                                <div class="ms">Bil.</div>
                                <div class="en">No.</div>
                            </th>

                            <th>
                                <div class="ms">Butiran</div>
                                <div class="en">Item</div>
                            </th>

                            <th style="text-align: right;">
                                <div class="ms">Jumlah</div>
                                <div class="en">Amount</div>
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
                        Jumlah Keseluruhan
                    </div>

                    <div class="en">
                        Total Amount
                    </div>
                </div>

                <div class="total-value">
                    RM {total_amount:,.2f}
                </div>
            </div>

            <div class="note">
                <div class="ms">
                    Sila maklum bahawa bagi pelanggan yang
                    membuat pembayaran, kemas kini baki akaun
                    akan diproses pada hari berikutnya.
                </div>

                <div class="en">
                    Please be informed that for customers making
                    payments, the account balance update will be
                    processed on the following day.
                </div>
            </div>

            <div class="download">
                <a
                    href="{pdf_url}"
                    target="_blank"
                    download
                >
                    <div class="ms">
                        Muat Turun Resit PDF
                    </div>

                    <div class="en">
                        Download PDF Receipt
                    </div>
                </a>
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
# BENTONG TAX RECEIPT PDF + HTML + QR
# =========================================================

@router.post("/receipt/qr/bentong")
def generate_bentong_tax_receipt(payload: dict):
    order_no = payload.get("order_no")
    paid_date_raw = payload.get("paid_date")
    payment_method = payload.get(
        "payment_method",
        "N/A",
    )
    bank_trx_no = payload.get("bank_trx_no")
    tax_items = payload.get("tax_items", [])

    if not order_no:
        raise HTTPException(
            status_code=400,
            detail=(
                "order_no diperlukan / "
                "Missing order_no"
            ),
        )

    if not tax_items:
        raise HTTPException(
            status_code=400,
            detail=(
                "Tiada item cukai diberikan / "
                "No tax items provided"
            ),
        )

    for index, item in enumerate(
        tax_items,
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

        if not item.get("owner_name"):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"owner_name tiada pada item {index} / "
                    f"Missing owner_name at item {index}"
                ),
            )

        if not item.get("property_address"):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"property_address tiada pada item {index} / "
                    f"Missing property_address at item {index}"
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

    pdf_bytes = generate_tax_receipt_bentong(
        paid_date=paid_date,
        payment_method=payment_method,
        tax_items=tax_items,
        order_no=order_no,
        bank_trx_no=bank_trx_no,
    )

    pdf_filename = (
        f"bentong_tax_receipt_{order_no}.pdf"
    )

    pdf_url = upload_to_blob(
        pdf_filename,
        pdf_bytes,
        content_type="application/pdf",
    )

    html_receipt = (
        generate_tax_receipt_bentong_html(
            paid_date=paid_date,
            payment_method=payment_method,
            tax_items=tax_items,
            pdf_url=pdf_url,
            order_no=order_no,
            bank_trx_no=bank_trx_no,
        )
    )

    html_filename = (
        f"bentong_tax_receipt_{order_no}.html"
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
# PAYMENT UPDATES - BENTONG TAX
# =========================================================

@router.post(
    "/payment-updates-cukaitaksiran-bentong"
)
def create_payment_updates_cukaitaksiran_bentong(
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
    tax_items = payload.get(
        "tax_items",
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

    if not tax_items:
        raise HTTPException(
            status_code=400,
            detail=(
                "Tiada item cukai diberikan / "
                "No tax items provided"
            ),
        )

    paid_date = _parse_paid_date(
        paid_date_raw
    )

    created_updates = []

    for index, item in enumerate(
        tax_items,
        start=1,
    ):
        required_fields = [
            "no_pendaftaran",
            "account_number",
            "owner_name",
            "property_address",
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
            PaymentUpdatesCukaiTaksiranBentong(
                order_no=order_no,
                no_pendaftaran=(
                    item.get("no_pendaftaran")
                ),
                account_number=(
                    item.get("account_number")
                ),
                owner_name=(
                    item.get("owner_name")
                ),
                property_address=(
                    item.get("property_address")
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
            "Rekod pembayaran berjaya dicipta / "
            "Payment updates created successfully"
        ),
        "total_records": len(created_updates),
        "data": created_updates,
    }


# =========================================================
# CHECK PAYMENT UPDATES
# =========================================================

@router.get(
    "/payment-updates-cukaitaksiran-bentong/semakan"
)
def semakan_payment_updates_cukaitaksiran_bentong(
    no_pendaftaran: str = None,
    account_number: str = None,
    db: Session = Depends(get_db),
):
    if (
        not no_pendaftaran
        and not account_number
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Sila berikan no_pendaftaran atau "
                "account_number / "
                "Please provide no_pendaftaran or "
                "account_number"
            ),
        )

    query = db.query(
        PaymentUpdatesCukaiTaksiranBentong
    )

    if account_number:
        query = query.filter(
            PaymentUpdatesCukaiTaksiranBentong
            .account_number
            == account_number
        )

    elif no_pendaftaran:
        query = query.filter(
            PaymentUpdatesCukaiTaksiranBentong
            .no_pendaftaran
            == no_pendaftaran
        )

    results = query.order_by(
        PaymentUpdatesCukaiTaksiranBentong
        .paid_date
        .desc()
    ).all()

    if not results:
        raise HTTPException(
            status_code=404,
            detail=(
                "Tiada rekod pembayaran dijumpai / "
                "No payment update found"
            ),
        )

    return results


# =========================================================
# MULTIPLE TAX RECEIPT
# TESTING / DEMO ONLY
# =========================================================

@router.post("/receipt/qr/multi")
def generate_multi_tax_receipt(
    payload: dict,
    db: Session = Depends(get_db),
):
    bill_numbers = payload.get(
        "bill_no",
        [],
    )

    if not bill_numbers:
        raise HTTPException(
            status_code=400,
            detail=(
                "Tiada nombor bil diberikan / "
                "No bill numbers provided"
            ),
        )

    taxes_data = []
    total_amount = 0.0

    for bill_no in bill_numbers:
        tax_obj = (
            db.query(CukaiTaksiran)
            .filter(
                CukaiTaksiran.bill_no
                == bill_no
            )
            .first()
        )

        if not tax_obj:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Bil {bill_no} tidak dijumpai / "
                    f"Bill {bill_no} not found"
                ),
            )

        property_obj = tax_obj.property

        owner_name = (
            tax_obj.owner_name
            or (
                tax_obj.owner.name
                if tax_obj.owner
                else "N/A"
            )
        )

        taxes_data.append(
            {
                "bill_no": tax_obj.bill_no,
                "property_type": (
                    property_obj.property_type
                    if property_obj
                    else "N/A"
                ),
                "lot_no": (
                    property_obj.lot_no
                    if property_obj
                    else ""
                ),
                "house_no": (
                    property_obj.house_no
                    if property_obj
                    else ""
                ),
                "street": (
                    property_obj.street
                    if property_obj
                    else ""
                ),
                "address1": (
                    property_obj.address1
                    if property_obj
                    else ""
                ),
                "address2": (
                    property_obj.address2
                    if property_obj
                    else ""
                ),
                "zone": (
                    property_obj.zone
                    if property_obj
                    else ""
                ),
                "amount": tax_obj.half_year_amount,
                "owner_name": owner_name,
            }
        )

        total_amount += _safe_float(
            tax_obj.half_year_amount
        )

    pdf_buffer = generate_multi_tax_pdf(
        taxes_data,
        total_amount,
    )

    pdf_filename = "multi_tax_receipt.pdf"

    pdf_url = upload_to_blob(
        pdf_filename,
        pdf_buffer.getvalue(),
        content_type="application/pdf",
    )

    rows_html = ""

    for tax in taxes_data:
        address_parts = [
            tax.get("lot_no", ""),
            tax.get("house_no", ""),
            tax.get("street", ""),
            tax.get("address1", ""),
            tax.get("address2", ""),
            tax.get("zone", ""),
        ]

        full_address = ", ".join(
            str(part)
            for part in address_parts
            if part
        )

        rows_html += f"""
        <tr>
            <td>{_safe_html(tax["bill_no"])}</td>
            <td>{_safe_html(tax["property_type"])}</td>
            <td>{_safe_html(full_address)}</td>
            <td class="money">
                RM {_safe_float(tax["amount"]):,.2f}
            </td>
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

    <title>
        Resit Pelbagai Cukai /
        Multiple Tax Receipt
    </title>

    <style>
        * {{
            box-sizing: border-box;
        }}

        body {{
            font-family:
                "Segoe UI",
                Tahoma,
                Arial,
                sans-serif;
            background: #e8ebef;
            padding: 25px;
            margin: 0;
            color: #111827;
        }}

        .receipt {{
            background: #ffffff;
            padding: 35px;
            max-width: 900px;
            border-radius: 16px;
            margin: 0 auto;
            box-shadow:
                0 6px 20px
                rgba(0, 0, 0, 0.08);
        }}

        .header {{
            background: #2f80ed;
            color: #ffffff;
            padding: 22px;
            text-align: center;
            border-radius: 12px;
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

        .table-container {{
            width: 100%;
            overflow-x: auto;
            margin-top: 25px;
            border: 1px solid #e5e7eb;
            border-radius: 10px;
        }}

        table {{
            border-collapse: collapse;
            width: 100%;
            min-width: 760px;
        }}

        th {{
            background: #f5f8ff;
            border-bottom:
                2px solid #d9e2f2;
            padding: 13px;
            text-align: center;
        }}

        th .ms {{
            color: #111827;
        }}

        th .en {{
            color: #4b5563;
            font-size: 12px;
        }}

        td {{
            padding: 13px;
            text-align: center;
            border-bottom:
                1px solid #eeeeee;
        }}

        tbody tr:nth-child(even) {{
            background: #fafafa;
        }}

        .money {{
            text-align: right;
            white-space: nowrap;
            font-weight: 700;
            color: #1d4ed8;
        }}

        .total {{
            margin-top: 22px;
            background: #f4f7ff;
            padding: 18px;
            border-left:
                6px solid #2f80ed;
            border-radius: 10px;
            display: flex;
            justify-content:
                space-between;
            align-items: center;
            gap: 20px;
        }}

        .total-value {{
            color: #1d4ed8;
            font-size: 24px;
            font-weight: 700;
            white-space: nowrap;
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
            border-radius: 10px;
            text-decoration: none;
        }}

        .pdf-button .ms,
        .pdf-button .en {{
            color: #ffffff;
        }}

        @media (max-width: 600px) {{
            body {{
                padding: 12px;
            }}

            .receipt {{
                padding: 20px 15px;
            }}

            .total {{
                display: block;
                text-align: center;
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
                Resit Pelbagai Cukai
            </div>

            <div class="en">
                Multiple Tax Receipt
            </div>
        </div>

        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>
                            <div class="ms">
                                No. Bil
                            </div>

                            <div class="en">
                                Bill No.
                            </div>
                        </th>

                        <th>
                            <div class="ms">
                                Jenis Harta
                            </div>

                            <div class="en">
                                Property Type
                            </div>
                        </th>

                        <th>
                            <div class="ms">
                                Alamat
                            </div>

                            <div class="en">
                                Address
                            </div>
                        </th>

                        <th>
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

        <div class="total">
            <div>
                <div class="ms">
                    Jumlah Keseluruhan
                </div>

                <div class="en">
                    Total Amount
                </div>
            </div>

            <div class="total-value">
                RM {total_amount:,.2f}
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
    </div>
</body>
</html>
    """

    html_filename = (
        "multi_tax_receipt.html"
    )

    html_url = upload_to_blob(
        html_filename,
        html_content.encode("utf-8"),
        content_type="text/html",
    )

    return _generate_qr_response(
        html_url
    )


# =========================================================
# PAY MULTIPLE TAXES
# TESTING / DEMO ONLY
# =========================================================

@router.post("/pay/multi")
def pay_multiple_taxes(
    payload: dict,
    db: Session = Depends(get_db),
    extra_days: int = 180,
):
    bill_numbers = payload.get(
        "bill_no",
        [],
    )

    if not bill_numbers:
        raise HTTPException(
            status_code=400,
            detail=(
                "Tiada nombor bil diberikan / "
                "No bill numbers provided"
            ),
        )

    updated_taxes = []
    total_amount = 0.0

    for bill_no in bill_numbers:
        tax = (
            db.query(CukaiTaksiran)
            .filter(
                CukaiTaksiran.bill_no
                == bill_no
            )
            .first()
        )

        if not tax:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Bil {bill_no} tidak dijumpai / "
                    f"Bill {bill_no} not found"
                ),
            )

        tax.due_date += timedelta(
            days=extra_days
        )

        total_amount += _safe_float(
            tax.half_year_amount
        )

        updated_taxes.append(tax)

    db.commit()

    for tax in updated_taxes:
        db.refresh(tax)

    return {
        "message": (
            "Pembayaran pelbagai bil cukai berjaya / "
            "Multiple tax bills paid successfully"
        ),
        "total_amount": round(
            total_amount,
            2,
        ),
        "paid_bills": [
            {
                "bill_no": tax.bill_no,
                "owner_name": tax.owner_name,
                "amount": tax.half_year_amount,
                "new_due_date": tax.due_date,
            }
            for tax in updated_taxes
        ],
    }