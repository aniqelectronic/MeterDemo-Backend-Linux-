from fastapi import APIRouter, Depends , HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fpdf import FPDF
import io
from io import BytesIO
import qrcode
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schema.compound.compound_schema import Compound
from app.models.compound.compound_model import CompoundCreate, CompoundResponse, StatusTypeEnum
import qrcode

from app.utils.blob_upload import upload_to_blob

# ----------------- CONFIG -----------------
from app.utils.config import BASE_URL

router = APIRouter(prefix="/compound", tags=["Compound"])

# --- Create compound ---

   
  # this is how to post data (for dummy test only)
  # {
   #  "compoundnum": "MBMBCMP2025000123",
   #  "plate": "ABC1234",
   # "date": "2025-09-22",
   #  "time": "15:45:00",
   #  "offense": "Illegal Parking",
   #  "amount": 50.0
 #   }
   
   
@router.post("/", response_model=CompoundResponse)
def create_compound(compound: CompoundCreate, db: Session = Depends(get_db)):
    new_compound = Compound(**compound.dict())
    db.add(new_compound)
    db.commit()
    db.refresh(new_compound)
    return new_compound
  
@router.post("/pay/{compoundnum}", response_model=CompoundResponse)
def pay_compound(compoundnum: str, db: Session = Depends(get_db)):
    # 1. Find compound
    compound = db.query(Compound).filter_by(compoundnum=compoundnum).first()
    if not compound:
        raise HTTPException(status_code=404, detail="Compound not found")

    # 2. Check if already paid
    if compound.status == StatusTypeEnum.paid:
        raise HTTPException(status_code=400, detail="Compound already paid")

    # 3. Update status
    compound.status = StatusTypeEnum.paid

    # 4. Save
    db.commit()
    db.refresh(compound)

    return compound

# --- Get all compounds ---
@router.get("/", response_model=list[CompoundResponse])
def get_compounds(db: Session = Depends(get_db)):
    return db.query(Compound).all()
  
# ---------------- GET ONE ----------------
@router.get("/{compound_id}", response_model=CompoundResponse)
def get_compound(compound_id: str, db: Session = Depends(get_db)):
    compound = db.query(Compound).filter(Compound.compoundnum == compound_id).first()
    if not compound:
        raise HTTPException(status_code=404, detail="Compound not found")
    return compound
  

# ================= COMPOUND RECEIPT QR =================
@router.get("/receipt/qr/{compoundnum}")
def view_compound_receipt(compoundnum: str, db: Session = Depends(get_db)):
    compound = db.query(Compound).filter(Compound.compoundnum == compoundnum).first()
    if not compound:
        raise HTTPException(status_code=404, detail="Compound not found")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Compound E-Receipt", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 8, f"Compound No: {compound.compoundnum}", ln=True)
    pdf.cell(0, 8, f"Plate: {compound.plate}", ln=True)
    pdf.cell(0, 8, f"Date: {compound.date}", ln=True)
    pdf.cell(0, 8, f"Time: {compound.time}", ln=True)
    pdf.cell(0, 8, f"Offense: {compound.offense}", ln=True)
    pdf.cell(0, 8, f"Amount: RM {compound.amount:.2f}", ln=True)
    pdf.ln(10)
    pdf.cell(0, 10, "Thank you for your payment!", ln=True, align="C")

    pdf_bytes = pdf.output(dest="S").encode("latin1")
    pdf_filename = f"compound_{compound.compoundnum}.pdf"
    pdf_url = upload_to_blob(pdf_filename, pdf_bytes, content_type="application/pdf")
    
    html = f"""
    <html>
        <head>
            <title>Compound E-Receipt</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    background: #f5f5f5;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                }}
                .receipt {{
                    background: white;
                    padding: 30px 40px;
                    border-radius: 15px;
                    box-shadow: 0 0 15px rgba(0,0,0,0.1);
                    width: 90%;
                    max-width: 600px;
                    font-size: 18px;
                    line-height: 1.6;
                }}
                h2 {{
                    color: #111;
                    text-align: center;
                    font-size: 26px;
                    margin-bottom: 25px;
                    letter-spacing: 0.5px;
                }}
                p {{
                    margin: 8px 0;
                    font-size: 17px;
                }}
                .thankyou {{
                    margin-top: 25px;
                    font-size: 20px;
                    font-weight: bold;
                    text-align: center;
                    color: #2a7a2a;
                }}
                .footer {{
                    margin-top: 25px;
                    font-size: 14px;
                    color: gray;
                    text-align: center;
                }}
                .download-btn {{
                    display: block;
                    text-align: center;
                    margin-top: 25px;
                }}
                .download-btn a {{
                    text-decoration: none;
                    background-color: #4CAF50;
                    color: white;
                    padding: 10px 25px;
                    font-size: 16px;
                    border-radius: 8px;
                    transition: 0.2s;
                }}
                .download-btn a:hover {{
                    background-color: #45a049;
                }}
                @media print {{
                    body {{
                        background: white;
                    }}
                    .receipt {{
                        box-shadow: none;
                        border: none;
                        width: 100%;
                        font-size: 16px;
                        padding: 20px;
                    }}
                    .download-btn {{ display: none; }}
                }}
            </style>
        </head>
        <body>
            <div class="receipt">
                <h2>Compound E-Receipt</h2>
                <p><b>Compound No:</b> {compound.compoundnum}</p>
                <p><b>Plate:</b> {compound.plate}</p>
                <p><b>Date:</b> {compound.date}</p>
                <p><b>Time:</b> {compound.time}</p>
                <p><b>Offense:</b> {compound.offense}</p>
                <p><b>Amount:</b> 
                    <span style="font-size:20px; font-weight:bold; color:#000;">
                        RM {compound.amount:.2f}
                    </span>
                </p>
    
                <div class="thankyou">Thank you for your payment</div>
    
                <div class="download-btn">
                    <a href="{pdf_url}" target="_blank">
                        Download PDF
                    </a>
                </div>
    
                <div class="footer">Generated by Parking System</div>
            </div>
        </body>
    </html>
    """
    
    
    html_bytes = html.encode("utf-8")
    filename = f"compound_{compound.compoundnum}.html"
    
    # ✅ Upload to Azure Blob
    blob_url = upload_to_blob(filename, html_bytes, content_type="text/html")
    
        # Generate QR for Blob URL
    receipt_url = blob_url
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(receipt_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")
    
    
@router.get("/html/qrdummy/{compoundnum}", response_class=HTMLResponse)
def qr_page(compoundnum: str):
    return f"""
    <html>
    <body style='text-align:center;margin-top:200px;'>
        <h1>Compound Payment</h1>
        <p>Compound No: {compoundnum}</p>
        <button style='font-size:30px;padding:20px;'
            onclick="fetch('/compound/pay/{compoundnum}', {{ method:'POST' }})
            .then(()=>alert('Payment Successful!'));"
        >
            PAY
        </button>
    </body>
    </html>
    """

# ---------------- Create dummy qr code payment image ----------------

@router.get("/qrdummy/{compoundnum}")
def generate_receipt_qr(compoundnum: str, db: Session = Depends(get_db)):

    # Use stored URL or generate if missing
    receipt_url =  f"{BASE_URL}/compound/html/qrdummy/{compoundnum}"

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(receipt_url)
    qr.make(fit=True)

    # Convert to image in memory
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")
