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
