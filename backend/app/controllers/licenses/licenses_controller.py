from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session
from fpdf import FPDF
from io import BytesIO
from datetime import date, timedelta
import qrcode

from app.db.database import get_db
from app.utils.blob_upload import upload_to_blob
from app.utils.config import BASE_URL
from app.models.licenses.licenses_model  import (
    LicenseCreate, LicenseResponse,
    OwnerLicenseCreate, OwnerLicenseResponse
)
from app.schema.licenses.licenses_schema import License, OwnerLicense
from app.controllers.licenses.licenses_receipt import generate_multi_license_pdf

router = APIRouter(prefix="/license", tags=["License"])

# ----------------- OWNER ENDPOINTS -----------------

@router.post("/owner", response_model=OwnerLicenseResponse)
def create_owner(owner: OwnerLicenseCreate, db: Session = Depends(get_db)):
    # Check if owner already exists
    existing = db.query(OwnerLicense).filter(OwnerLicense.ic == owner.ic).first()
    if existing:
        raise HTTPException(status_code=400, detail="Owner with this IC already exists")

    new_owner = OwnerLicense(
        ic=owner.ic,
        name=owner.name,
        email=owner.email,
        address=owner.address
    )
    db.add(new_owner)
    db.commit()
    db.refresh(new_owner)
    return new_owner

# ----------------- LICENSE ENDPOINTS -----------------

# Create a new license
@router.post("/", response_model=LicenseResponse)
def create_license(license: LicenseCreate, db: Session = Depends(get_db)):
    # Ensure owner exists
    owner = db.query(OwnerLicense).filter(OwnerLicense.ic == license.ic).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    # Auto-detect license type
    if "BIZ" in license.licensenum:
        licensetype = "Business License"
    elif "HBR" in license.licensenum:
        licensetype = "Entertainment / Buskers License"
    elif "IKL" in license.licensenum:
        licensetype = "Advertisement License"
    elif "KOM" in license.licensenum:
        licensetype = "Composite License"
    else:
        licensetype = "Unknown"

    # Start date today, end date +1 year
    today = date.today()
    end_date = today + timedelta(days=365)

    new_license = License(
        licensenum=license.licensenum,
        licensetype=licensetype,
        ic=license.ic,
        amount=license.amount,
        start_date=today,
        end_date=end_date
    )

    db.add(new_license)
    db.commit()
    db.refresh(new_license)
    return new_license


# Pay license
@router.post("/pay/{licensenum}", response_model=LicenseResponse)
def pay_license(licensenum: str, db: Session = Depends(get_db)):
    license_obj = db.query(License).filter(License.licensenum == licensenum).first()
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")

    # If end_date is in the past or today, start from today
    today = date.today()
    if not license_obj.end_date or license_obj.end_date < today:
        license_obj.start_date = today
        license_obj.end_date = today + timedelta(days=365)
    else:
        # Renew: extend end_date by 1 year from current end_date
        license_obj.end_date = license_obj.end_date + timedelta(days=365)

    db.commit()
    db.refresh(license_obj)
    return license_obj


# Get all licenses
@router.get("/", response_model=list[LicenseResponse])
def get_licenses(db: Session = Depends(get_db)):
    return db.query(License).all()

# Get single license by number
@router.get("/{licensenum}", response_model=LicenseResponse)
def get_license(licensenum: str, db: Session = Depends(get_db)):
    license_obj = db.query(License).filter(License.licensenum == licensenum).first()
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")
    return license_obj

# License receipt with QR
@router.get("/receipt/qr/{licensenum}", response_class=HTMLResponse)
def view_license_receipt(licensenum: str, db: Session = Depends(get_db)):
    license_obj = db.query(License).filter(License.licensenum == licensenum).first()
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")

    owner = db.query(OwnerLicense).filter(OwnerLicense.ic == license_obj.ic).first()
    owner_name = owner.name if owner else "N/A"

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "License E-Receipt", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 8, f"License No: {license_obj.licensenum}", ln=True)
    pdf.cell(0, 8, f"Type: {license_obj.licensetype}", ln=True)
    pdf.cell(0, 8, f"Owner IC: {license_obj.ic}", ln=True)
    pdf.cell(0, 8, f"Owner Name: {owner_name}", ln=True)
    pdf.cell(0, 8, f"Amount: RM {license_obj.amount:.2f}", ln=True)
    pdf.cell(0, 8, f"Start Date: {license_obj.start_date}", ln=True)
    pdf.cell(0, 8, f"End Date: {license_obj.end_date}", ln=True)

    pdf_bytes = pdf.output(dest="S").encode("latin1")
    pdf_filename = f"license_{license_obj.licensenum}.pdf"
    pdf_url = upload_to_blob(pdf_filename, pdf_bytes, content_type="application/pdf")

    html = f"""
    <html>
        <body style="font-family:Arial;text-align:center;padding:30px;">
            <h2>License E-Receipt</h2>
            <p><b>License No:</b> {license_obj.licensenum}</p>
            <p><b>Type:</b> {license_obj.licensetype}</p>
            <p><b>Owner IC:</b> {license_obj.ic}</p>
            <p><b>Owner Name:</b> {owner_name}</p>
            <p><b>Amount:</b> RM {license_obj.amount:.2f}</p>
            <p><b>Start Date:</b> {license_obj.start_date}</p>
            <p><b>End Date:</b> {license_obj.end_date}</p>
            <a href="{pdf_url}" target="_blank">Download PDF</a>
        </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.post("/receipt/qr/multi")
def generate_multi_license_receipt(payload: dict, db: Session = Depends(get_db)):
    """
    Payload example:
    {
        "licenses": ["BIZ2025001", "BIZ2025002"]
    }
    """

    license_numbers = payload.get("licenses", [])

    if not license_numbers:
        raise HTTPException(status_code=400, detail="No license numbers provided")

    licenses_data = []
    total_amount = 0.0

    # --- Fetch all licenses from DB ---
    for lic in license_numbers:
        lic_obj = db.query(License).filter(License.licensenum == lic).first()
        if not lic_obj:
            raise HTTPException(status_code=404, detail=f"License {lic} not found")

        owner = db.query(OwnerLicense).filter(OwnerLicense.ic == lic_obj.ic).first()
        owner_name = owner.name if owner else "N/A"

        licenses_data.append({
            "licensenumber": lic_obj.licensenum,
            "licensetype": lic_obj.licensetype,
            "expired_date": lic_obj.end_date,
            "amount": lic_obj.amount,
            "owner_name": owner_name,
            "ic": lic_obj.ic
        })

        total_amount += lic_obj.amount

    # === Generate PDF ===
    pdf_buffer = generate_multi_license_pdf(licenses_data, total_amount)
    pdf_filename = "multi_license_receipt.pdf"
    pdf_url = upload_to_blob(
        pdf_filename,
        pdf_buffer.getvalue(),
        content_type="application/pdf"
    )

    # --- Generate table rows ---
    rows_html = ""
    for c in licenses_data:
        rows_html += f"""
            <tr>
                <td>{c['licensenumber']}</td>
                <td>{c['licensetype']}</td>
                <td>{c['expired_date']}</td>
                <td>RM {float(c['amount']):.2f}</td>
            </tr>
        """

    # --- HTML Receipt ---
    html = f"""
    <html>
    <head>
        <title>License Receipt</title>
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
                max-width: 750px;
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
                overflow-x: auto;       /* Enable horizontal scroll */
                margin-top: 25px;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                min-width: 600px;       /* Ensure table is wide enough */
                white-space: nowrap;     /* Prevent text wrapping */
                table-layout: auto;      /* Columns size based on content */
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
        <div class="header">Multiple License Receipt</div>

        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>License Number</th>
                        <th>License Type</th>
                        <th>Expired Date</th>
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
    filename = "multi_license_receipt.html"
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




# Get all licenses by owner IC
@router.get("/by-ic/{ic}", response_model=list[LicenseResponse])
def get_licenses_by_ic(ic: str, db: Session = Depends(get_db)):
    # Check if owner exists
    owner = db.query(OwnerLicense).filter(OwnerLicense.ic == ic).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    # Get all licenses for this owner
    licenses = db.query(License).filter(License.ic == ic).all()
    return licenses