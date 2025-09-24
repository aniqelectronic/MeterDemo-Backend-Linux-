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


# ----------------- CONFIG -----------------
BASE_IP = "192.168.0.100"  # <-- change only this if IP changes
BASE_URL = f"http://{BASE_IP}:8000"  # used for receipt URLs

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
  
  # ✅ Get single compound by ID
@router.get("/{compound_id}", response_model=CompoundResponse)
def get_compound(compound_id: str, db: Session = Depends(get_db)):
    compound = db.query(Compound).filter(Compound.compoundnum == compound_id).first()
    if not compound:
        raise HTTPException(status_code=404, detail="Compound not found")
    return compound
  

# ================= RECEIPT (HTML PAGE) =================
@router.get("/receipt/view/{compoundnum}", response_class=HTMLResponse)
def view_compound_receipt(compoundnum: str, db: Session = Depends(get_db)):
    compound = db.query(Compound).filter(Compound.compoundnum == compoundnum).first()
    if not compound:
        raise HTTPException(status_code=404, detail="Compound not found")

    html = f"""
    <html>
        <head>
            <title>Compound E-Receipt</title>
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
                <h2>Compound E-Receipt</h2>
                <p><b>Compound No:</b> {compound.compoundnum}</p>
                <p><b>Plate:</b> {compound.plate}</p>
                <p><b>Date:</b> {compound.date}</p>
                <p><b>Time:</b> {compound.time}</p>
                <p><b>Offense:</b> {compound.offense}</p>
                <p><b>Amount:</b> RM {compound.amount:.2f}</p>
                <div class="thankyou">Thank you for your payment!</div>

                <!-- PDF download button -->
                <div class="download-btn">
                    <a href="/compound/receipt/pdf/{compound.compoundnum}" target="_blank">
                        Download PDF
                    </a>
                </div>

                <div class="footer">Generated by Parking System</div>
            </div>
        </body>
    </html>
    """
    return HTMLResponse(content=html)


# ================= RECEIPT PDF =================
@router.get("/receipt/pdf/{compoundnum}")
def download_compound_receipt_pdf(compoundnum: str, db: Session = Depends(get_db)):
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

    # write PDF into memory
    pdf_bytes = pdf.output(dest="S").encode("latin1")
    buffer = io.BytesIO(pdf_bytes)

    return StreamingResponse(buffer, media_type="application/pdf", headers={
        "Content-Disposition": f"inline; filename=compound_{compound.compoundnum}.pdf"
    })
    
    
# ================= COMPOUND RECEIPT QR =================
@router.get("/receipt/qr/{compoundnum}")
def generate_compound_receipt_qr(compoundnum: str, db: Session = Depends(get_db)):
    compound = db.query(Compound).filter(Compound.compoundnum == compoundnum).first()
    if not compound:
        raise HTTPException(status_code=404, detail="Compound not found")

    # This QR points to the HTML receipt page
    receipt_url = f"{BASE_URL}/compound/receipt/view/{compound.compoundnum}"

    qr = qrcode.make(receipt_url)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)

    return StreamingResponse(buffer, media_type="image/png")

# ---------------- GET LATEST COMPOUND QR CODE ----------------
@router.get("/latest/qr")
def get_latest_compound_qr(db: Session = Depends(get_db)):
    """
    Get the latest compound and return its QR code (PNG).
    """
    tx = db.query(Compound).order_by(Compound.id.desc()).first()
    if not tx:
        raise HTTPException(status_code=404, detail="No compounds found")

    # Always refresh receipt URL
    receipt_url = f"{BASE_URL}/compound/receipt/view/{tx.compoundnum}"
    # If you want to store receipt_url inside DB, uncomment this part
    # if tx.receipt_url != receipt_url:
    #     tx.receipt_url = receipt_url
    #     db.commit()

    # Generate QR code
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
