from fastapi import APIRouter, Depends , HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fpdf import FPDF
import io
from io import BytesIO
import qrcode
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schema.compound.compound_schema import Compound, MultiCompound
from app.models.compound.compound_model import CompoundCreate, CompoundResponse, StatusTypeEnum
from app.models.compound.multicompound_model import MultiCompoundBase, MultiCompoundCreate , MultiCompoundResponse
import qrcode
import html
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


# ================= COMPOUND RECEIPT QR =================
@router.post("/receipt/qr/single")
def view_compound_receipt(body: CompoundCreate):

    # ================= VALIDATE BODY ==================
    if not body.compoundnum:
        raise HTTPException(status_code=400, detail="Compound number required")

    # Escape HTML to avoid breaking formatting
    compound = body
    compound_name = html.escape(compound.name or "-")
    compound_no = html.escape(compound.compoundnum)
    compound_plate = html.escape(compound.plate or "-")
    compound_date = html.escape(compound.date or "-")
    compound_time = html.escape(compound.time or "-")
    compound_offense = html.escape(compound.offense or "-")
    compound_status = html.escape(compound.status.value if compound.status else "-")
    compound_amount = f"{compound.amount:.2f}"

    # ================= PDF GENERATION ==================
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Compound E-Receipt", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 8, f"Name: {compound_name}", ln=True)
    pdf.cell(0, 8, f"Compound No: {compound_no}", ln=True)
    pdf.cell(0, 8, f"Plate: {compound_plate}", ln=True)
    pdf.cell(0, 8, f"Date: {compound_date}", ln=True)
    pdf.cell(0, 8, f"Time: {compound_time}", ln=True)
    pdf.cell(0, 8, f"Offense: {compound_offense}", ln=True)
    pdf.cell(0, 8, f"Amount: RM {compound_amount}", ln=True)
    pdf.cell(0, 8, f"Status: {compound_status}", ln=True)

    pdf.ln(10)
    pdf.cell(0, 10, "Thank you for your payment!", ln=True, align="C")

    pdf_bytes = pdf.output(dest="S").encode("latin1")
    pdf_filename = f"compound_{compound_no}.pdf"

    pdf_url = upload_to_blob(
        pdf_filename,
        pdf_bytes,
        content_type="application/pdf"
    )

    # ================= HTML RECEIPT ==================
    html_content = f"""
    <html>
    <head>
        <title>Compound Receipt</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, sans-serif;
                background: #eceff1;
                margin: 0;
                padding: 25px;
                display: flex;
                justify-content: center;
            }}

            .receipt {{
                background: white;
                border-radius: 16px;
                padding: 30px 35px;
                width: 100%;
                max-width: 650px;
                box-shadow: 0 6px 18px rgba(0,0,0,0.08);
            }}

            .header {{
                background: #2F80ED;
                color: white;
                padding: 20px;
                border-radius: 12px;
                text-align: center;
                font-size: 24px;
                font-weight: bold;
            }}

            .info-section {{
                margin-top: 25px;
                font-size: 17px;
                color: #333;
            }}

            .info-row {{
                display: flex;
                justify-content: space-between;
                padding: 10px 0;
                border-bottom: 1px solid #eee;
            }}

            .info-label {{
                font-weight: 600;
            }}

            .amount-box {{
                margin-top: 25px;
                padding: 18px;
                background: #f4f7ff;
                border-left: 6px solid #2F80ED;
                border-radius: 10px;
                font-size: 20px;
                font-weight: bold;
                color: #2F80ED;
                text-align: center;
            }}

            .thankyou {{
                margin-top: 30px;
                font-size: 19px;
                font-weight: bold;
                color: #27ae60;
                text-align: center;
            }}

            .download-btn {{
                margin-top: 35px;
                text-align: center;
            }}

            .download-btn a {{
                background: #2F80ED;
                padding: 12px 30px;
                font-size: 17px;
                color: white;
                border-radius: 10px;
                text-decoration: none;
            }}

            .footer {{
                margin-top: 25px;
                text-align: center;
                font-size: 14px;
                color: gray;
            }}
        </style>
    </head>
    <body>

    <div class="receipt">
        <div class="header">Compound Receipt</div>

        <div class="info-section">
            <div class="info-row"><span class="info-label">Name:</span> <span>{compound_name}</span></div>
            <div class="info-row"><span class="info-label">Compound No:</span> <span>{compound_no}</span></div>
            <div class="info-row"><span class="info-label">Plate No:</span> <span>{compound_plate}</span></div>
            <div class="info-row"><span class="info-label">Date:</span> <span>{compound_date}</span></div>
            <div class="info-row"><span class="info-label">Time:</span> <span>{compound_time}</span></div>
            <div class="info-row"><span class="info-label">Offense:</span> <span>{compound_offense}</span></div>
            <div class="info-row"><span class="info-label">Status:</span> <span>{compound_status}</span></div>
        </div>

        <div class="amount-box">Amount: RM {compound_amount}</div>

        <div class="thankyou">Thank you for your payment!</div>

        <div class="download-btn">
            <a href="{pdf_url}" target="_blank">Download PDF</a>
        </div>

        <div class="footer">Generated by Parking System</div>
    </div>

    </body>
    </html>
    """

    html_bytes = html_content.encode("utf-8")
    html_filename = f"compound_{compound_no}.html"

    html_url = upload_to_blob(
        html_filename,
        html_bytes,
        content_type="text/html"
    )

    # ================= QR GENERATION ==================
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4
    )
    qr.add_data(html_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")


    
    
# ================= GET UNPAID COMPOUNDS BY PLATE =================
@router.get("/unpaid/{plate}", response_model=list[CompoundResponse])
def get_unpaid_compounds_by_plate(plate: str, db: Session = Depends(get_db)):
    compounds = (
        db.query(Compound)
        .filter(Compound.plate == plate, Compound.status == StatusTypeEnum.unpaid)
        .all()
    )
    
    if not compounds:
        raise HTTPException(status_code=404, detail="No unpaid compounds found for this plate")
    
    return compounds

# ================= MULTI COMPOUND PAYMENT =================
@router.post("/multi/pay", response_model=list[MultiCompoundResponse])
def pay_multiple_compounds(payload: list[MultiCompoundCreate], db: Session = Depends(get_db)):
    """
    Example payload:
    [
        {"transaction_bank_id": "BANKTXN123456", "compoundnum": "MBMBCMP2025000123"},
        {"transaction_bank_id": "BANKTXN123456", "compoundnum": "MBMBCMP2025000456"}
    ]
    """

    transaction_id = payload[0].transaction_bank_id  # all should share same ID
    saved_entries = []

    for item in payload:
        # 1️⃣ Verify compound exists
        compound = db.query(Compound).filter_by(compoundnum=item.compoundnum).first()
        if not compound:
            raise HTTPException(status_code=404, detail=f"Compound {item.compoundnum} not found")

        # 2️⃣ Mark as paid if not already
        if compound.status == StatusTypeEnum.paid:
            continue  # already paid, skip
        compound.status = StatusTypeEnum.paid
        db.add(compound)

        # 3️⃣ Record mapping in MultiCompound
        record = MultiCompound(transaction_bank_id=transaction_id, compoundnum=item.compoundnum)
        db.add(record)
        saved_entries.append(record)

    db.commit()
    db.refresh(saved_entries[0])  # refresh first one to make sure ORM flush works

    return saved_entries



@router.get("/multi/{transaction_bank_id}", response_model=list[MultiCompoundResponse])
def get_compounds_by_transaction(transaction_bank_id: str, db: Session = Depends(get_db)):
    results = db.query(MultiCompound).filter_by(transaction_bank_id=transaction_bank_id).all()
    if not results:
        raise HTTPException(status_code=404, detail="No compounds found for this transaction")
    return results


# ================= UPDATE MULTIPLE COMPOUNDS TO PAID =================
@router.put("/multi/update")
def update_multiple_compounds_to_paid(data: dict, db: Session = Depends(get_db)):
    """
    Example payload:
    {
        "compound_numbers": ["MBPPCMP20252", "MBPPCMP20253"]
    }
    """
    compound_numbers = data.get("compound_numbers")

    if not compound_numbers or not isinstance(compound_numbers, list):
        raise HTTPException(status_code=400, detail="compound_numbers must be a list")

    updated = []
    skipped = []

    for comp_num in compound_numbers:
        compound = db.query(Compound).filter_by(compoundnum=comp_num).first()
        if not compound:
            skipped.append({"compoundnum": comp_num, "reason": "Not found"})
            continue
        if compound.status == StatusTypeEnum.paid:
            skipped.append({"compoundnum": comp_num, "reason": "Already paid"})
            continue

        compound.status = StatusTypeEnum.paid
        db.add(compound)
        updated.append(comp_num)

    db.commit()

    return {
        "message": f"{len(updated)} compounds updated to PAID.",
        "updated_compounds": updated,
        "skipped": skipped
    }


@router.post("/receipt/qr/multi")
def generate_multi_compound_receipt(payload: dict):
    """
    Example payload:
    {
        "compounds": [
            {"compoundnum": "MBMBCMP2025000123", "amount": 50.0},
            {"compoundnum": "MBMBCMP2025000456", "amount": 70.0}
        ],
        "total_amount": 120.0
    }
    """

    compounds = payload.get("compounds", [])
    total_amount = payload.get("total_amount", 0.0)

    if not compounds:
        raise HTTPException(status_code=400, detail="No compounds provided")

    # --- Generate table rows ---
    rows_html = ""
    for c in compounds:
        rows_html += f"""
            <tr>
                <td>{c.get("compoundnum")}</td>
                <td>RM {float(c.get("amount", 0)):.2f}</td>
            </tr>
        """

    # --- Build HTML receipt ---
    html = f"""
   <html>
   <head>
       <title>Multi-Compound Receipt</title>
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
               width: 100%;
               max-width: 750px;
               border-radius: 16px;
               box-shadow: 0px 6px 20px rgba(0,0,0,0.08);
               margin: 0 auto;
               
               /* IMPORTANT FIXES */
               height: auto !important;
               overflow: visible !important;
           }}
   
           .header {{
               background: #2F80ED;
               color: white;
               padding: 18px;
               font-size: 24px;
               text-align: center;
               border-radius: 12px;
           }}
   
           table {{
               width: 100%;
               border-collapse: collapse;
               margin-top: 25px;
   
               /* Allow multi-page tables */
               page-break-inside: auto;
           }}
   
           thead {{
               display: table-header-group; /* Required for page-breaks */
           }}
   
           tbody {{
               display: table-row-group;
           }}
   
           tr {{
               page-break-inside: avoid;
               page-break-after: auto;
           }}
   
           th {{
               background: #f5f8ff;
               padding: 12px;
               border-bottom: 2px solid #e0e0e0;
               font-size: 16px;
               font-weight: bold;
           }}
   
           td {{
               padding: 12px;
               text-align: center;
               border-bottom: 1px solid #eee;
               font-size: 16px;
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
   
           .thankyou {{
               margin-top: 30px;
               color: #27ae60;
               text-align: center;
               font-size: 20px;
               font-weight: bold;
           }}
   
           .footer {{
               margin-top: 25px;
               text-align: center;
               font-size: 14px;
               color: gray;
           }}
   
           @media print {{
   
               body {{
                   background: white;
                   padding: 0;
               }}
   
               .receipt {{
                   box-shadow: none;
                   padding: 20px;
                   height: auto !important;
                   overflow: visible !important;
               }}
   
               table, tr, td, th {{
                   page-break-inside: avoid !important;
               }}
           }}
       </style>
   </head>
   <body>
   
   <div class="receipt">
   
       <div class="header">Multiple Compound Receipt</div>
   
       <table>
           <thead>
               <tr>
                   <th>Compound Number</th>
                   <th>Amount (RM)</th>
               </tr>
           </thead>
   
           <tbody>
               {rows_html}
           </tbody>
       </table>
   
       <div class="total">
           Total: RM {float(total_amount):.2f}
       </div>
   
       <div class="thankyou">Thank you for your payment!</div>
   
       <div class="footer">Generated by Parking System</div>
   
   </div>
   
   </body>
   </html>
   """


    # --- Upload HTML to Azure Blob ---
    html_bytes = html.encode("utf-8")
    filename = f"multi_compound_receipt.html"
    blob_url = upload_to_blob(filename, html_bytes, content_type="text/html")

    # --- Generate QR for the HTML receipt ---
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(blob_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")
