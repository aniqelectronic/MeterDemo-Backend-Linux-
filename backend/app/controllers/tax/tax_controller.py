from datetime import datetime, timedelta
from io import BytesIO
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import qrcode
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.tax.tax_model import OwnerCreate, PropertyCreate, TaxCreate, TaxResponse
from app.schema.tax.tax_schema import CukaiTaksiran, Owner, Property
from app.controllers.tax.tax_receipt import generate_multi_tax_pdf
from app.utils.blob_upload import upload_to_blob 


import html
from datetime import datetime
from io import BytesIO

import qrcode

from app.controllers.tax.tax_receipt_bentong import generate_tax_receipt_bentong

router = APIRouter(prefix="/tax", tags=["Cukai Taksiran"])

# --- Create new owner ---
@router.post("/owner", response_model=OwnerCreate)
def create_owner(owner: OwnerCreate, db: Session = Depends(get_db)):
    new_owner = Owner(**owner.dict())
    db.add(new_owner)
    db.commit()
    db.refresh(new_owner)
    return new_owner

# --- Create new property ---
@router.post("/property", response_model=PropertyCreate)
def create_property(prop: PropertyCreate, db: Session = Depends(get_db)):
    new_prop = Property(**prop.dict())
    db.add(new_prop)
    db.commit()
    db.refresh(new_prop)
    return new_prop

# --- Create multiple taxes ---
@router.post("/", response_model=List[TaxResponse])
def create_multiple_taxes(taxes: List[TaxCreate], db: Session = Depends(get_db)):
    created_taxes = []
    for tax in taxes:
        # Fetch owner to set correct owner_name
        owner = db.query(Owner).filter(Owner.id == tax.owner_id).first()
        if not owner:
            raise HTTPException(status_code=404, detail=f"Owner ID {tax.owner_id} not found")

        tax_data = tax.dict()
        tax_data['owner_name'] = owner.name

        new_tax = CukaiTaksiran(**tax_data)

        # Adjust issue_date and due_date to Malaysia time (UTC+8)
        if new_tax.issue_date:
            new_tax.issue_date += timedelta(hours=8)
        if new_tax.due_date:
            new_tax.due_date += timedelta(hours=8)

        db.add(new_tax)
        db.commit()
        db.refresh(new_tax)
        created_taxes.append(new_tax)
    return created_taxes

# --- Get all taxes ---
@router.get("/", response_model=List[TaxResponse])
def get_taxes(db: Session = Depends(get_db)):
    return db.query(CukaiTaksiran).all()

# --- Get single tax by bill_no ---
@router.get("/{bill_no}", response_model=TaxResponse)
def get_tax(bill_no: str, db: Session = Depends(get_db)):
    tax = db.query(CukaiTaksiran).filter(CukaiTaksiran.bill_no == bill_no).first()
    if not tax:
        raise HTTPException(status_code=404, detail="Tax not found")

    # Dynamically add property_type
    result = tax.__dict__
    result['property_type'] = tax.property.property_type
    return result


# --- Get taxes by owner IC ---
@router.get("/by-ic/{ic}")
def get_taxes_by_ic_with_property_type(ic: str, db: Session = Depends(get_db)):
    owner = db.query(Owner).filter(Owner.ic == ic).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    
    taxes = db.query(CukaiTaksiran).filter(CukaiTaksiran.owner_id == owner.id).all()
    if not taxes:
        raise HTTPException(status_code=404, detail="No taxes found for this owner")
    
    # Add property_type for each tax
    result = []
    for tax in taxes:
        tax_dict = tax.__dict__.copy()  # convert to dict
        tax_dict['property_type'] = tax.property.property_type
        result.append(tax_dict)
    
    return result


# --- Renew tax by extending due_date or creating new record ---
@router.post("/renew/{bill_no}", response_model=TaxResponse)
def renew_tax(bill_no: str, db: Session = Depends(get_db), extra_days: int = 180):
    tax = db.query(CukaiTaksiran).filter(CukaiTaksiran.bill_no == bill_no).first()
    if not tax:
        raise HTTPException(status_code=404, detail="Tax bill not found")
    
    # Extend the due_date by extra_days (default 180 days = 6 months)
    tax.due_date += timedelta(days=extra_days)

    db.add(tax)
    db.commit()
    db.refresh(tax)
    return tax


def generate_tax_receipt_bentong_html(
    paid_date: datetime,
    payment_method: str,
    tax_items: list,
    pdf_url: str,
    order_no: str,
    bank_trx_no: str = None,
):
    total_amount = sum(float(item.get("amount", 0) or 0) for item in tax_items)

    rows_html = ""

    for index, item in enumerate(tax_items, start=1):
        account_number = html.escape(str(item.get("account_number", "-")))
        owner_name = html.escape(str(item.get("owner_name", "-")))
        property_address = html.escape(str(item.get("property_address", "-")))
        amount = float(item.get("amount", 0) or 0)

        rows_html += f"""
        <tr>
            <td class="no">{index}</td>
            <td>
                <div class="item-title">Assessment Tax</div>
                <div>Account Number: {account_number}</div>
                <div>Owner Name: {owner_name}</div>
                <div>Property Address:</div>
                <div class="address">{property_address}</div>
            </td>
            <td class="amount">RM {amount:,.2f}</td>
        </tr>
        """

    bank_html = ""
    if bank_trx_no:
        bank_html = f"""
        <p><strong>Bank Transaction No:</strong> {html.escape(str(bank_trx_no))}</p>
        """

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Bentong Tax Receipt</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <style>
        body {{
            margin: 0;
            padding: 30px;
            background: #eef3f8;
            font-family: Arial, Helvetica, sans-serif;
            color: #222;
        }}

        .receipt {{
            max-width: 820px;
            margin: auto;
            background: white;
            border-radius: 18px;
            overflow: hidden;
            box-shadow: 0 8px 25px rgba(0,0,0,0.10);
        }}

        .header {{
            background: linear-gradient(135deg, #12A8E0, #083B73);
            color: white;
            padding: 30px 40px;
        }}

        .header h2 {{
            margin: 0 0 8px 0;
            font-size: 22px;
        }}

        .header p {{
            margin: 3px 0;
            font-size: 13px;
        }}

        .content {{
            padding: 35px 40px;
        }}

        .title-row {{
            display: flex;
            justify-content: space-between;
            gap: 20px;
            border-bottom: 1px solid #e5e5e5;
            padding-bottom: 22px;
            flex-wrap: wrap;
        }}

        h1 {{
            margin: 0;
            font-size: 34px;
        }}

        .receipt-no {{
            color: #666;
            font-weight: bold;
            margin-top: 5px;
        }}

        .meta p {{
            margin: 6px 0;
            font-size: 14px;
            color: #444;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 30px;
        }}

        th {{
            background: #083B73;
            color: white;
            padding: 13px;
            font-size: 14px;
            text-align: left;
        }}

        td {{
            padding: 16px 13px;
            border-bottom: 1px solid #eeeeee;
            vertical-align: top;
            font-size: 14px;
        }}

        .no {{
            width: 45px;
        }}

        .item-title {{
            font-weight: bold;
            font-size: 15px;
            margin-bottom: 8px;
        }}

        .address {{
            margin-top: 3px;
            color: #444;
            line-height: 1.4;
        }}

        .amount {{
            text-align: right;
            white-space: nowrap;
            font-weight: bold;
        }}

        .total {{
            background: #083B73;
            color: white;
            margin-top: 25px;
            padding: 16px 20px;
            border-radius: 12px;
            text-align: right;
            font-size: 22px;
            font-weight: bold;
        }}

        .note {{
            text-align: center;
            color: #666;
            font-size: 12px;
            margin-top: 25px;
            line-height: 1.5;
        }}

        .download {{
            text-align: center;
            margin-top: 30px;
        }}

        .download a {{
            display: inline-block;
            background: #27ae60;
            color: white;
            padding: 14px 26px;
            border-radius: 12px;
            text-decoration: none;
            font-size: 17px;
            font-weight: bold;
        }}

        .footer {{
            background: #f6f8fb;
            text-align: center;
            padding: 22px;
            color: #666;
            font-size: 13px;
            line-height: 1.5;
        }}
    </style>
</head>

<body>
    <div class="receipt">
        <div class="header">
            <h2>Majlis Perbandaran Bentong</h2>
            <p>Jalan Ketari</p>
            <p>28700 Bentong, Pahang Darul Makmur</p>
            <p>Telephone : 04-5497555</p>
            <p>Application : TIP Bentong</p>
        </div>

        <div class="content">
            <div class="title-row">
                <div>
                    <h1>Receipt</h1>
                    <div class="receipt-no">#{html.escape(str(order_no))}</div>
                </div>

                <div class="meta">
                    <p><strong>Paid at:</strong> {paid_date.strftime("%d %b %Y")}</p>
                    <p><strong>Payment Method:</strong> {html.escape(str(payment_method))}</p>
                    {bank_html}
                </div>
            </div>

            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Item</th>
                        <th style="text-align:right;">Amount</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>

            <div class="total">
                RM {total_amount:,.2f}
            </div>

            <div class="note">
                Please be informed that for customers making payments, the updating of account balances will be processed on the following day.
            </div>

            <div class="download">
                <a href="{pdf_url}" target="_blank" download>Download PDF Receipt</a>
            </div>
        </div>

        <div class="footer">
            Majlis Perbandaran Bentong<br>
            Jalan Ketari, 28700 Bentong, Pahang Darul Makmur<br>
            Telephone : 04-5497555 | Application : TIP Bentong
        </div>
    </div>
</body>
</html>
"""


@router.post("/receipt/qr/bentong")
def generate_bentong_tax_receipt(payload: dict):
    order_no = payload.get("order_no")
    paid_date_raw = payload.get("paid_date")
    payment_method = payload.get("payment_method", "N/A")
    bank_trx_no = payload.get("bank_trx_no")
    tax_items = payload.get("tax_items", [])

    if not order_no:
        raise HTTPException(status_code=400, detail="Missing order_no")

    if not tax_items:
        raise HTTPException(status_code=400, detail="No tax items provided")

    for index, item in enumerate(tax_items, start=1):
        if not item.get("account_number"):
            raise HTTPException(status_code=400, detail=f"Missing account_number at item {index}")
        if not item.get("owner_name"):
            raise HTTPException(status_code=400, detail=f"Missing owner_name at item {index}")
        if not item.get("property_address"):
            raise HTTPException(status_code=400, detail=f"Missing property_address at item {index}")
        if item.get("amount") is None:
            raise HTTPException(status_code=400, detail=f"Missing amount at item {index}")

    if paid_date_raw:
        paid_date = datetime.fromisoformat(paid_date_raw)
    else:
        paid_date = datetime.now()

    pdf_bytes = generate_tax_receipt_bentong(
        paid_date=paid_date,
        payment_method=payment_method,
        tax_items=tax_items,
        order_no=order_no,
        bank_trx_no=bank_trx_no,
    )

    pdf_filename = f"bentong_tax_receipt_{order_no}.pdf"

    pdf_url = upload_to_blob(
        pdf_filename,
        pdf_bytes,
        content_type="application/pdf",
    )

    html_receipt = generate_tax_receipt_bentong_html(
        paid_date=paid_date,
        payment_method=payment_method,
        tax_items=tax_items,
        pdf_url=pdf_url,
        order_no=order_no,
        bank_trx_no=bank_trx_no,
    )

    html_filename = f"bentong_tax_receipt_{order_no}.html"

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

@router.post("/receipt/qr/multi")
def generate_multi_tax_receipt(payload: dict, db: Session = Depends(get_db)):
    """
    Payload example:
    {
        "bill_no": ["BILL2025001", "BILL2025002"]
    }
    """
    bill_nos = payload.get("bill_no", [])

    if not bill_nos:
        raise HTTPException(status_code=400, detail="No bill numbers provided")

    taxes_data = []
    total_amount = 0.0

    # --- Fetch all tax records from DB ---
    for bill_no in bill_nos:
        tax_obj = db.query(CukaiTaksiran).filter(CukaiTaksiran.bill_no == bill_no).first()
        if not tax_obj:
            raise HTTPException(status_code=404, detail=f"Bill {bill_no} not found")

        prop = tax_obj.property
        owner_name = tax_obj.owner_name or (tax_obj.owner.name if tax_obj.owner else "N/A")

        taxes_data.append({
            "bill_no": tax_obj.bill_no,
            "property_type": prop.property_type if prop else "N/A",
            "lot_no": prop.lot_no if prop else "",
            "house_no": prop.house_no if prop else "",
            "street": prop.street if prop else "",
            "address1": prop.address1 if prop else "",
            "address2": prop.address2 if prop else "",
            "zone": prop.zone if prop else "",
            "amount": tax_obj.half_year_amount,
            "owner_name": owner_name
        })

        total_amount += tax_obj.half_year_amount

    # === Generate PDF ===
    pdf_buffer = generate_multi_tax_pdf(taxes_data, total_amount)
    pdf_filename = "multi_tax_receipt.pdf"
    pdf_url = upload_to_blob(
        pdf_filename,
        pdf_buffer.getvalue(),
        content_type="application/pdf"
    )

    # --- Generate table rows for HTML ---
    rows_html = ""
    for t in taxes_data:
        address_parts = [
            t.get("lot_no", ""),
            t.get("house_no", ""),
            t.get("street", ""),
            t.get("address1", ""),
            t.get("address2", ""),
            t.get("zone", "")
        ]
        full_address = ", ".join([p for p in address_parts if p])

        rows_html += f"""
            <tr>
                <td>{t['bill_no']}</td>
                <td>{t['property_type']}</td>
                <td>{full_address}</td>
                <td>RM {float(t['amount']):.2f}</td>
            </tr>
        """

    # --- HTML Receipt ---
    html = f"""
    <html>
    <head>
        <title>Tax Receipt</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, sans-serif;
                background: #e8ebef;
                padding: 25px;
                margin: 0;
            }}
            .receipt {{
                background: white;
                padding: 35px;
                max-width: 800px;
                border-radius: 16px;
                margin: 0 auto;
                box-shadow: 0px 6px 20px rgba(0,0,0,0.08);
            }}
            .header {{
                background: #2F80ED;
                color: white;
                padding: 18px;
                font-size: 24px;
                text-align: center;
                border-radius: 12px;
            }}
            .table-container {{
                width: 100%;
                overflow-x: auto;
                margin-top: 25px;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                min-width: 700px;
                white-space: nowrap;
                table-layout: auto;
            }}
            th {{
                background: #f5f8ff;
                border-bottom: 2px solid #e0e0e0;
                padding: 12px;
                font-size: 16px;
                font-weight: bold;
                text-align: center;
            }}
            td {{
                padding: 12px;
                text-align: center;
                border-bottom: 1px solid #eee;
            }}
            .total {{
                margin-top: 20px;
                background: #f4f7ff;
                padding: 15px;
                font-size: 20px;
                font-weight: bold;
                border-left: 6px solid #2F80ED;
                border-radius: 10px;
                text-align: right;
            }}
            .pdf-button {{
                margin-top: 25px;
                text-align: center;
            }}
            .pdf-button a {{
                background: #27ae60;
                padding: 12px 20px;
                color: white;
                font-size: 18px;
                border-radius: 10px;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>

    <div class="receipt">
        <div class="header">Multiple Tax Receipt</div>

        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Bill No.</th>
                        <th>Property Type</th>
                        <th>Address</th>
                        <th>Amount (RM)</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>

        <div class="total">
            Total: RM {float(total_amount):.2f}
        </div>

        <div class="pdf-button">
            <a href="{pdf_url}" target="_blank">Download PDF Receipt</a>
        </div>
    </div>

    </body>
    </html>
    """

    # --- Upload HTML ---
    html_bytes = html.encode("utf-8")
    filename = "multi_tax_receipt.html"
    blob_url = upload_to_blob(filename, html_bytes, content_type="text/html")

    # --- Generate QR ---
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L)
    qr.add_data(blob_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")


@router.post("/pay/multi")
def pay_multiple_taxes(
    payload: dict,
    db: Session = Depends(get_db),
    extra_days: int = 180
):
    """
    Payload example:
    {
        "bill_no": ["BILL2025001", "BILL2025002"]
    }
    """

    bill_nos = payload.get("bill_no", [])

    if not bill_nos:
        raise HTTPException(status_code=400, detail="No bill numbers provided")

    updated_taxes = []
    total_amount = 0.0

    for bill_no in bill_nos:
        tax = db.query(CukaiTaksiran).filter(
            CukaiTaksiran.bill_no == bill_no
        ).first()

        if not tax:
            raise HTTPException(status_code=404, detail=f"Bill {bill_no} not found")

        # Extend due date
        tax.due_date += timedelta(days=extra_days)

        total_amount += tax.half_year_amount
        updated_taxes.append(tax)

    db.commit()

    for tax in updated_taxes:
        db.refresh(tax)

    return {
        "message": "Multiple tax bills paid successfully",
        "total_amount": round(total_amount, 2),
        "paid_bills": [
            {
                "bill_no": t.bill_no,
                "owner_name": t.owner_name,
                "amount": t.half_year_amount,
                "new_due_date": t.due_date
            }
            for t in updated_taxes
        ]
    }
    
    
    
    
    
