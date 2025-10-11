from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schema.licenses.licenses_schema import License
from app.models.licenses.licenses_model import LicenseCreate, LicenseResponse, StatusTypeEnum
from fpdf import FPDF
import io
import qrcode
from io import BytesIO
from datetime import date, timedelta

# ----------------- CONFIG -----------------
BASE_IP = "192.168.0.100"   # same IP config as compound
BASE_URL = f"http://{BASE_IP}:8000"

router = APIRouter(prefix="/license", tags=["License"])


# --- Helper function to detect license type & year ---
def parse_license_details(licensenum: str):
    if "BIZ" in licensenum:
        licensetype = "Business License"
    elif "HBR" in licensenum:
        licensetype = "Entertainment / Buskers License"
    elif "IKL" in licensenum:
        licensetype = "Advertisement License"
    elif "KOM" in licensenum:
        licensetype = "Composite License"
    else:
        licensetype = "Unknown"

    year = int(licensenum[7:11])    
    return licensetype, year


# --- Create a new license ---
@router.post("/", response_model=LicenseResponse)
def create_license(license: LicenseCreate, db: Session = Depends(get_db)):
    licensetype, year = parse_license_details(license.licensenum)
    new_license = License(
        licensenum=license.licensenum,
        licensetype=licensetype,
        owner_id=license.owner_id,
        year=year,
        amount=license.amount,
        status=StatusTypeEnum.unpaid,   # default unpaid
        start_date=None,
        end_date=None
    )
    db.add(new_license)
    db.commit()
    db.refresh(new_license)
    return new_license


# --- Pay license ---
@router.post("/pay/{licensenum}", response_model=LicenseResponse)
def pay_license(licensenum: str, db: Session = Depends(get_db)):
    license_obj = db.query(License).filter(License.licensenum == licensenum).first()
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")

    if license_obj.status == StatusTypeEnum.active:
        raise HTTPException(status_code=400, detail="License already active")

    # Activate license
    license_obj.status = StatusTypeEnum.active
    license_obj.start_date = date.today()
    license_obj.end_date = license_obj.start_date + timedelta(days=365)

    db.commit()
    db.refresh(license_obj)
    return license_obj


# --- Auto-expire check ---
def check_expiry(license_obj: License, db: Session):
    if license_obj.end_date and date.today() > license_obj.end_date:
        license_obj.status = StatusTypeEnum.expired
        db.commit()
        db.refresh(license_obj)
    return license_obj


# --- Get all licenses ---
@router.get("/", response_model=list[LicenseResponse])
def get_licenses(db: Session = Depends(get_db)):
    licenses = db.query(License).all()
    return [check_expiry(l, db) for l in licenses]


# --- Get single license by ID ---
@router.get("/{license_id}", response_model=LicenseResponse)
def get_license(license_id: str, db: Session = Depends(get_db)):
    license_obj = db.query(License).filter(License.licensenum == license_id).first()
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")
    return check_expiry(license_obj, db)


# ================= LICENSE RECEIPT (HTML PAGE) =================
@router.get("/receipt/view/{licensenum}", response_class=HTMLResponse)
def view_license_receipt(licensenum: str, db: Session = Depends(get_db)):
    license_obj = db.query(License).filter(License.licensenum == licensenum).first()
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")

    license_obj = check_expiry(license_obj, db)

    html = f"""
    <html>
        <head>
            <title>License E-Receipt</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 30px;
                    padding: 20px;
                    background: #f9f9f9;
                }}
                .receipt {{
                    background: white;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0 0 10px rgba(0,0,0,0.1);
                    max-width: 400px;
                }}
                h2 {{ color: #333; }}
                p {{ margin: 6px 0; }}
                .thankyou {{
                    margin-top: 20px;
                    font-size: 16px;
                    font-weight: bold;
                    text-align: center;
                }}
                .footer {{
                    margin-top: 20px;
                    font-size: 12px;
                    color: gray;
                }}
                .download-btn {{
                    display: block;
                    width: 100%;
                    text-align: center;
                    margin-top: 15px;
                }}
                .download-btn a {{
                    text-decoration: none;
                    background-color: #4CAF50;
                    color: white;
                    padding: 10px 20px;
                    border-radius: 5px;
                }}
            </style>
        </head>
        <body>
            <div class="receipt">
                <h2>License E-Receipt</h2>
                <p><b>License No:</b> {license_obj.licensenum}</p>
                <p><b>Type:</b> {license_obj.licensetype}</p>
                <p><b>Year:</b> {license_obj.year}</p>
                <p><b>Owner ID:</b> {license_obj.owner_id}</p>
                <p><b>Amount:</b> RM {license_obj.amount:.2f}</p>
                <p><b>Status:</b> {license_obj.status}</p>
                <p><b>Start Date:</b> {license_obj.start_date}</p>
                <p><b>End Date:</b> {license_obj.end_date}</p>
                <div class="thankyou">Thank you for your payment!</div>

                <div class="download-btn">
                    <a href="/license/receipt/pdf/{license_obj.licensenum}" target="_blank">
                        Download PDF
                    </a>
                </div>

                <div class="footer">Generated by License System</div>
            </div>
        </body>
    </html>
    """
    return HTMLResponse(content=html)


# ================= LICENSE RECEIPT PDF =================
@router.get("/receipt/pdf/{licensenum}")
def download_license_receipt_pdf(licensenum: str, db: Session = Depends(get_db)):
    license_obj = db.query(License).filter(License.licensenum == licensenum).first()
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")

    license_obj = check_expiry(license_obj, db)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "License E-Receipt", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 8, f"License No: {license_obj.licensenum}", ln=True)
    pdf.cell(0, 8, f"Type: {license_obj.licensetype}", ln=True)
    pdf.cell(0, 8, f"Year: {license_obj.year}", ln=True)
    pdf.cell(0, 8, f"Owner: {license_obj.owner_id}", ln=True)
    pdf.cell(0, 8, f"Amount: RM {license_obj.amount:.2f}", ln=True)
    pdf.cell(0, 8, f"Status: {license_obj.status}", ln=True)
    pdf.cell(0, 8, f"Start Date: {license_obj.start_date}", ln=True)
    pdf.cell(0, 8, f"End Date: {license_obj.end_date}", ln=True)
    pdf.ln(10)
    pdf.cell(0, 10, "Thank you for your payment!", ln=True, align="C")

    pdf_bytes = pdf.output(dest="S").encode("latin1")
    buffer = io.BytesIO(pdf_bytes)

    return StreamingResponse(buffer, media_type="application/pdf", headers={
        "Content-Disposition": f"inline; filename=license_{license_obj.licensenum}.pdf"
    })


# ================= LICENSE RECEIPT QR =================
@router.get("/receipt/qr/{licensenum}")
def generate_license_receipt_qr(licensenum: str, db: Session = Depends(get_db)):
    license_obj = db.query(License).filter(License.licensenum == licensenum).first()
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")

    receipt_url = f"{BASE_URL}/license/receipt/view/{license_obj.licensenum}"

    qr = qrcode.make(receipt_url)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)

    return StreamingResponse(buffer, media_type="image/png")


# ================= LICENSE QR DUMMY PAYMENT =================
@router.get("/html/qrdummy/{licensenum}", response_class=HTMLResponse)
def qr_page(licensenum: str):
    return f"""
    <html>
    <body style='text-align:center;margin-top:200px;'>
        <h1>License Payment</h1>
        <p>License No: {licensenum}</p>
        <button style='font-size:30px;padding:20px;'
            onclick="fetch('/license/pay/{licensenum}', {{ method:'POST' }})
            .then(()=>alert('Payment Successful!'));"
        >
            PAY
        </button>
    </body>
    </html>
    """


@router.get("/qrdummy/{licensenum}")
def generate_receipt_qr(licensenum: str, db: Session = Depends(get_db)):
    receipt_url = f"{BASE_URL}/license/html/qrdummy/{licensenum}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(receipt_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")
