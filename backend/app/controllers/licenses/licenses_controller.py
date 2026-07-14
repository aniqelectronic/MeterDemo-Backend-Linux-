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
        raise HTTPException(status_code=400, detail="Pemilik dengan nombor IC ini telah wujud / Owner with this IC already exists")

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
        raise HTTPException(status_code=404, detail="Pemilik tidak dijumpai / Owner not found")

    # Auto-detect license type
    if "BIZ" in license.licensenum:
        licensetype = "Lesen Perniagaan / Business License"
    elif "HBR" in license.licensenum:
        licensetype = "Lesen Hiburan / Penghibur Jalanan / Entertainment / Buskers License"
    elif "IKL" in license.licensenum:
        licensetype = "Lesen Iklan / Advertisement License"
    elif "KOM" in license.licensenum:
        licensetype = "Lesen Komposit / Composite License"
    else:
        licensetype = "Tidak Diketahui / Unknown"

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
        raise HTTPException(status_code=404, detail="Lesen tidak dijumpai / License not found")

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

@router.post("/pay-multi")
def pay_multiple_licenses(payload: dict, db: Session = Depends(get_db)):
    """
    Payload example:
    {
        "licenses": ["BIZ2025001", "BIZ2025002"]
    }
    """

    license_numbers = payload.get("licenses")
    
    if not isinstance(license_numbers, list):
        raise HTTPException(
            status_code=400,
            detail="licenses mesti dalam bentuk senarai nombor lesen / licenses must be a list of license numbers"
        )
    
    license_numbers = [lic.strip() for lic in license_numbers if lic.strip()]
    
    if not license_numbers:
        raise HTTPException(
            status_code=400,
            detail="Tiada nombor lesen yang sah diberikan / No valid license numbers provided"
        )
    

    today = date.today()
    updated_licenses = []
    total_amount = 0.0

    # --- Fetch & update licenses ---
    for lic_no in license_numbers:
        lic = db.query(License).filter(License.licensenum == lic_no).first()
        if not lic:
            raise HTTPException(status_code=404, detail=f"Lesen {lic_no} tidak dijumpai / License {lic_no} not found")

        # Renew logic
        if not lic.end_date or lic.end_date < today:
            lic.start_date = today
            lic.end_date = today + timedelta(days=365)
        else:
            lic.end_date = lic.end_date + timedelta(days=365)

        total_amount += lic.amount
        updated_licenses.append(lic)

    db.commit()

    # Refresh all updated objects
    for lic in updated_licenses:
        db.refresh(lic)

    return {
        "message": "Pembayaran pelbagai lesen berjaya / Multiple licenses paid successfully",
        "total_amount": round(total_amount, 2),
        "count": len(updated_licenses)
    }


# Get single license by number
@router.get("/{licensenum}", response_model=LicenseResponse)
def get_license(licensenum: str, db: Session = Depends(get_db)):
    license_obj = db.query(License).filter(License.licensenum == licensenum).first()
    if not license_obj:
        raise HTTPException(status_code=404, detail="Lesen tidak dijumpai / License not found")
    return license_obj

# License receipt with QR
@router.get("/receipt/qr/{licensenum}", response_class=HTMLResponse)
def view_license_receipt(licensenum: str, db: Session = Depends(get_db)):
    license_obj = db.query(License).filter(License.licensenum == licensenum).first()
    if not license_obj:
        raise HTTPException(status_code=404, detail="Lesen tidak dijumpai / License not found")

    owner = db.query(OwnerLicense).filter(OwnerLicense.ic == license_obj.ic).first()
    owner_name = owner.name if owner else "N/A"

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "E-Resit Lesen / License E-Receipt", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 8, f"No. Lesen / License No: {license_obj.licensenum}", ln=True)
    pdf.cell(0, 8, f"Jenis Lesen / License Type: {license_obj.licensetype}", ln=True)
    pdf.cell(0, 8, f"No. IC Pemilik / Owner IC: {license_obj.ic}", ln=True)
    pdf.cell(0, 8, f"Nama Pemilik / Owner Name: {owner_name}", ln=True)
    pdf.cell(0, 8, f"Jumlah / Amount: RM {license_obj.amount:.2f}", ln=True)
    pdf.cell(0, 8, f"Tarikh Mula / Start Date: {license_obj.start_date}", ln=True)
    pdf.cell(0, 8, f"Tarikh Tamat / End Date: {license_obj.end_date}", ln=True)

    pdf_bytes = pdf.output(dest="S").encode("latin1")
    pdf_filename = f"license_{license_obj.licensenum}.pdf"
    pdf_url = upload_to_blob(pdf_filename, pdf_bytes, content_type="application/pdf")

    html = f"""
    <!DOCTYPE html>
    <html lang="ms">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta name="color-scheme" content="only light">
        <title>E-Resit Lesen / License E-Receipt</title>

        <style>
            * {{
                box-sizing: border-box;
            }}

            body {{
                font-family: "Segoe UI", Arial, sans-serif;
                background: #e8ebef;
                color: #111827;
                padding: 25px;
                margin: 0;
            }}

            .receipt {{
                background: #ffffff;
                max-width: 750px;
                margin: 0 auto;
                border-radius: 16px;
                overflow: hidden;
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
            }}

            .header {{
                background: #2f80ed;
                color: #ffffff;
                padding: 24px;
                text-align: center;
            }}

            .header h1 {{
                margin: 0;
                font-size: 28px;
            }}

            .header p {{
                margin: 8px 0 0;
                font-size: 15px;
                opacity: 0.95;
            }}

            .content {{
                padding: 30px 35px;
            }}

            .details {{
                background: #f8faff;
                border: 1px solid #e1e8f5;
                border-radius: 12px;
                padding: 12px 22px;
            }}

            .detail-row {{
                display: flex;
                justify-content: space-between;
                gap: 20px;
                padding: 13px 0;
                border-bottom: 1px dashed #d6dce8;
            }}

            .detail-row:last-child {{
                border-bottom: none;
            }}

            .label {{
                font-weight: 700;
                text-align: left;
            }}

            .value {{
                text-align: right;
                word-break: break-word;
            }}

            .amount {{
                margin-top: 22px;
                padding: 18px;
                background: #eaf2ff;
                border-left: 6px solid #2f80ed;
                border-radius: 10px;
                text-align: right;
                font-size: 22px;
                font-weight: 700;
            }}

            .amount span {{
                color: #1d4ed8;
                font-size: 26px;
            }}

            .thank-you {{
                margin-top: 28px;
                text-align: center;
                color: #15803d;
                font-size: 18px;
                font-weight: 600;
            }}

            .pdf-button {{
                margin-top: 28px;
                text-align: center;
            }}

            .pdf-button a {{
                display: inline-block;
                background: #27ae60;
                color: #ffffff;
                padding: 13px 24px;
                border-radius: 10px;
                text-decoration: none;
                font-size: 17px;
                font-weight: 600;
            }}

            .footer {{
                margin-top: 30px;
                text-align: center;
                color: #6b7280;
                font-size: 13px;
            }}

            @media (max-width: 600px) {{
                body {{
                    padding: 12px;
                }}

                .content {{
                    padding: 22px 18px;
                }}

                .detail-row {{
                    display: block;
                }}

                .value {{
                    margin-top: 5px;
                    text-align: left;
                }}
            }}
        </style>
    </head>

    <body>
        <div class="receipt">
            <div class="header">
                <h1>E-Resit Lesen / License E-Receipt</h1>
                <p>Rekod Transaksi Rasmi / Official Transaction Record</p>
            </div>

            <div class="content">
                <div class="details">
                    <div class="detail-row">
                        <div class="label">No. Lesen / License No.</div>
                        <div class="value">{license_obj.licensenum}</div>
                    </div>

                    <div class="detail-row">
                        <div class="label">Jenis Lesen / License Type</div>
                        <div class="value">{license_obj.licensetype}</div>
                    </div>

                    <div class="detail-row">
                        <div class="label">No. IC Pemilik / Owner IC</div>
                        <div class="value">{license_obj.ic}</div>
                    </div>

                    <div class="detail-row">
                        <div class="label">Nama Pemilik / Owner Name</div>
                        <div class="value">{owner_name}</div>
                    </div>

                    <div class="detail-row">
                        <div class="label">Tarikh Mula / Start Date</div>
                        <div class="value">{license_obj.start_date}</div>
                    </div>

                    <div class="detail-row">
                        <div class="label">Tarikh Tamat / End Date</div>
                        <div class="value">{license_obj.end_date}</div>
                    </div>
                </div>

                <div class="amount">
                    Jumlah Dibayar / Total Paid:
                    <span>RM {license_obj.amount:.2f}</span>
                </div>

                <div class="thank-you">
                    Terima kasih atas pembayaran anda.<br>
                    Thank you for your payment.
                </div>

                <div class="pdf-button">
                    <a href="{pdf_url}" target="_blank">
                        Muat Turun Resit PDF / Download PDF Receipt
                    </a>
                </div>

                <div class="footer">
                    &copy; 2025 City Car Park System &bull;
                    Hak Cipta Terpelihara / All Rights Reserved
                </div>
            </div>
        </div>
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
        raise HTTPException(status_code=400, detail="Tiada nombor lesen diberikan / No license numbers provided")

    licenses_data = []
    total_amount = 0.0

    # --- Fetch all licenses from DB ---
    for lic in license_numbers:
        lic_obj = db.query(License).filter(License.licensenum == lic).first()
        if not lic_obj:
            raise HTTPException(status_code=404, detail=f"Lesen {lic} tidak dijumpai / License {lic} not found")

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

    # --- Bilingual HTML Receipt ---
    html = f"""
    <!DOCTYPE html>
    <html lang="ms">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta name="color-scheme" content="only light">

        <title>Resit Pelbagai Lesen / Multiple License Receipt</title>

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
                max-width: 850px;
                border-radius: 16px;
                margin: 0 auto;
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
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
                border-collapse: collapse;
                width: 100%;
                min-width: 700px;
                white-space: nowrap;
                table-layout: auto;
            }}

            th {{
                background: #f5f8ff;
                border-bottom: 2px solid #d9e2f2;
                padding: 13px 12px;
                font-size: 15px;
                font-weight: 700;
                text-align: center;
                color: #1f2937;
            }}

            th small {{
                display: block;
                margin-top: 3px;
                font-size: 12px;
                font-weight: 500;
                color: #4b5563;
            }}

            td {{
                padding: 13px 12px;
                text-align: center;
                border-bottom: 1px solid #eeeeee;
            }}

            tbody tr:last-child td {{
                border-bottom: none;
            }}

            tbody tr:nth-child(even) {{
                background: #fafafa;
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

            .thank-you {{
                margin-top: 28px;
                text-align: center;
                color: #15803d;
                font-size: 18px;
                font-weight: 600;
            }}

            .pdf-button {{
                margin-top: 26px;
                text-align: center;
            }}

            .pdf-button a {{
                display: inline-block;
                background: #27ae60;
                padding: 13px 22px;
                color: #ffffff;
                font-size: 17px;
                font-weight: 600;
                border-radius: 10px;
                text-decoration: none;
            }}

            .footer {{
                margin-top: 30px;
                text-align: center;
                color: #6b7280;
                font-size: 13px;
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
            }}
        </style>
    </head>

    <body>
        <div class="receipt">
            <div class="header">
                <h1>Resit Pelbagai Lesen / Multiple License Receipt</h1>
                <p>Rekod Transaksi Rasmi / Official Transaction Record</p>
            </div>

            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>
                                No. Lesen
                                <small>License Number</small>
                            </th>

                            <th>
                                Jenis Lesen
                                <small>License Type</small>
                            </th>

                            <th>
                                Tarikh Luput
                                <small>Expiry Date</small>
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
                <span>RM {float(total_amount):.2f}</span>
            </div>

            <div class="thank-you">
                Terima kasih atas pembayaran anda.<br>
                Thank you for your payment.
            </div>

            <div class="pdf-button">
                <a href="{pdf_url}" target="_blank">
                    Muat Turun Resit PDF / Download PDF Receipt
                </a>
            </div>

            <div class="footer">
                &copy; 2025 City Car Park System &bull;
                Hak Cipta Terpelihara / All Rights Reserved
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
        raise HTTPException(status_code=404, detail="Pemilik tidak dijumpai / Owner not found")

    # Get all licenses for this owner
    licenses = db.query(License).filter(License.ic == ic).all()
    return licenses