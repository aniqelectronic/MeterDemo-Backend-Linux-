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

    # Auto-detect license type (optional)
    licensetype = license.licensetype or "Unknown"
    if "BIZ" in license.licensenum:
        licensetype = "Business License"
    elif "HBR" in license.licensenum:
        licensetype = "Entertainment / Buskers License"
    elif "IKL" in license.licensenum:
        licensetype = "Advertisement License"
    elif "KOM" in license.licensenum:
        licensetype = "Composite License"

    new_license = License(
        licensenum=license.licensenum,
        licensetype=licensetype,
        ic=license.ic,
        amount=license.amount,
        start_date=None,
        end_date=None
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

    # Set start and end dates
    license_obj.start_date = date.today()
    license_obj.end_date = license_obj.start_date + timedelta(days=365)

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
