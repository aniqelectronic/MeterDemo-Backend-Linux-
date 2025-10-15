# app/controllers/transaction_parking_controller.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, cast , Integer
from fastapi.responses import HTMLResponse, FileResponse , StreamingResponse
from app.db.database import get_db
from app.schema.parking.transaction_parking_schema import TransactionParking
from app.models.parking.transaction_parking_model import TransactionResponse
from app.utils.blob_upload import upload_to_blob




from app.schema.parking.parking_schema import Parking


from fpdf import FPDF
import os
import qrcode
from io import BytesIO

# ----------------- CONFIG -----------------
from app.utils.config import BASE_URL

router = APIRouter(prefix="/transactions", tags=["Transactions"])


# ---------------- GET ALL ----------------
@router.get("/", response_model=list[TransactionResponse])
def get_all_transactions(db: Session = Depends(get_db)):
    transactions = db.query(TransactionParking).all()
    if not transactions:
        return []

    for tx in transactions:
        # dynamically add receipt_url to the object (even if already in DB)
        tx.receipt_url = f"{BASE_URL}/transactions/receipt/view/{tx.ticket_id}"
        db.commit()
    return transactions


# ---------------- RECEIPT (HTML PAGE) ----------------
@router.get("/receipt/view/{ticket_id}", response_class=HTMLResponse)
def view_receipt(ticket_id: str, db: Session = Depends(get_db)):
    transaction = db.query(TransactionParking).filter(TransactionParking.ticket_id == ticket_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    parking = db.query(Parking).filter(Parking.plate == transaction.plate).order_by(Parking.id.desc()).first()
    tx_type = transaction.transaction_type.value if transaction.transaction_type else "N/A"

    html = f"""
    <html>
        <head>
            <title>Parking E-Receipt</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    background: #f0f0f0;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                }}
                .receipt {{
                    background: white;
                    padding: 60px;
                    border-radius: 20px;
                    box-shadow: 0 0 30px rgba(0,0,0,0.2);
                    width: 700px;
                    font-size: 32px;    /* 🔹 Bigger text */
                    line-height: 1.6;
                }}
                h2 {{
                    color: #111;
                    text-align: center;
                    font-size: 40px;     /* 🔹 Large heading */
                    margin-bottom: 40px;
                    letter-spacing: 1px;
                }}
                p {{
                    margin: 12px 0;
                    font-size: 30px;     /* 🔹 Bigger paragraph text */
                }}
                .thankyou {{
                    margin-top: 40px;
                    font-size: 36px;     /* 🔹 Large thank-you message */
                    font-weight: bold;
                    text-align: center;
                    color: #2a7a2a;
                }}
                .footer {{
                    margin-top: 40px;
                    font-size: 22px;
                    color: gray;
                    text-align: center;
                }}
                .download-btn {{
                    display: block;
                    text-align: center;
                    margin-top: 35px;
                }}
                .download-btn a {{
                    text-decoration: none;
                    background-color: #4CAF50;
                    color: white;
                    padding: 20px 50px;
                    font-size: 28px;      /* 🔹 Larger button */
                    border-radius: 10px;
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
                        font-size: 28px;
                        padding: 30px;
                    }}
                    .download-btn {{ display: none; }}
                }}
            </style>
        </head>
        <body>
            <div class="receipt">
                <h2>Parking E-Receipt</h2>
                <p><b>Ticket ID:</b> {transaction.ticket_id}</p>
                <p><b>Plate:</b> {transaction.plate}</p>
                <p><b>Time Purchased (Hours):</b> {transaction.hours}</p>
                <p><b>Time In:</b> {parking.timein if parking else "N/A"}</p>
                <p><b>Time Out:</b> {parking.timeout if parking else "N/A"}</p>
                <p><b>Amount:</b> 
                    <span style="font-size:38px; font-weight:bold; color:#000;">
                        RM {transaction.amount:.2f}
                    </span>
                </p>
                <p><b>Transaction Type:</b> {tx_type}</p>
    
                <div class="thankyou">Thank you! Drive safely </div>
    
                <div class="download-btn">
                    <a href="/transactions/receipt/pdf/{transaction.ticket_id}" target="_blank">
                        Download PDF
                    </a>
                </div>
    
                <div class="footer">Generated by Parking System</div>
            </div>
        </body>
    </html>
    """
    html_bytes = html.encode("utf-8")
    filename = f"receipt_{transaction.ticket_id}.html"
    html_url = upload_to_blob(filename, html_bytes, content_type="text/html")

    transaction.receipt_url = html_url
    db.commit()

    return {"receipt_url": html_url}

# ---------------- RECEIPT PDF ----------------
from fastapi.responses import StreamingResponse
import io
from fpdf import FPDF

@router.get("/receipt/pdf/{ticket_id}")
def download_receipt_pdf(ticket_id: str, db: Session = Depends(get_db)):
    transaction = db.query(TransactionParking).filter(TransactionParking.ticket_id == ticket_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Ticket not found")

    parking = db.query(Parking).filter(Parking.plate == transaction.plate).order_by(Parking.id.desc()).first()
    tx_type = transaction.transaction_type.value if transaction.transaction_type else "N/A"

    # create PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Parking E-Receipt", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 8, f"Ticket ID: {transaction.ticket_id}", ln=True)
    pdf.cell(0, 8, f"Plate: {transaction.plate}", ln=True)
    pdf.cell(0, 8, f"Time Purchased (Hours): {transaction.hours}", ln=True)
    pdf.cell(0, 8, f"Time In: {parking.timein if parking else 'N/A'}", ln=True)
    pdf.cell(0, 8, f"Time Out: {parking.timeout if parking else 'N/A'}", ln=True)
    pdf.cell(0, 8, f"Amount: RM {transaction.amount:.2f}", ln=True)
    pdf.cell(0, 8, f"Transaction Type: {tx_type}", ln=True)
    pdf.ln(10)
    pdf.cell(0, 10, "Thank you!! Drive safely", ln=True, align="C")

    pdf_bytes = pdf.output(dest="S").encode("latin1")
    buffer = io.BytesIO(pdf_bytes)
    # Upload to Azure
    #filename = f"receipt_{transaction.ticket_id}.pdf"
    #receipt_url = upload_to_blob(filename, pdf_bytes, content_type="application/pdf")

    return StreamingResponse(buffer, media_type="application/pdf", headers={
        "Content-Disposition": f"inline; filename=compound_{transaction.ticket_id}.pdf"
    })


# ---------------- QR CODE ----------------
""""
This will give you the Qr code for the receipt of the ticket id that you given 
example in postman :

Get http://192.168.22.15:8000/transactions/receipt/qr/P-0006

so it will give the specific P-0006 ticket qr code

"""
@router.get("/receipt/qr/{ticket_id}")
def generate_receipt_qr(ticket_id: str, db: Session = Depends(get_db)):
    """
    Generate a QR code for the receipt URL stored in DB.
    """
    transaction = db.query(TransactionParking).filter(TransactionParking.ticket_id == ticket_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Use stored URL or generate if missing
    receipt_url =  f"{BASE_URL}/transactions/receipt/view/{transaction.ticket_id}"

    # Save URL to DB if missing or outdated
    if transaction.receipt_url != receipt_url:
        transaction.receipt_url = receipt_url
        db.commit()
    
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

# ---------------- GET LATEST TRANSACTION ----------------
"""
This is for getting latest ticket url
"""
@router.get("/latest")
def get_latest_transaction(db: Session = Depends(get_db)):
    """
    Get the latest transaction based on auto-increment `id`
    and return its receipt URL.
    """
    tx = db.query(TransactionParking).order_by(TransactionParking.id.desc()).first()
    print(tx)

    if not tx:
        raise HTTPException(status_code=404, detail="No transactions found")

    # Always refresh receipt URL
    tx.receipt_url =  f"{BASE_URL}/transactions/receipt/view/{tx.ticket_id}"
    db.commit()

    return {"receipt_url": tx.receipt_url}

# ---------------- GET BY TICKET ----------------
"""
Get the all ticket info 
"""
@router.get("/{ticket_id}", response_model=TransactionResponse)
def get_transaction_by_ticket(ticket_id: str, db: Session = Depends(get_db)):
    """
    Get a single transaction by ticket_id with receipt_url.
    """
    tx = db.query(TransactionParking).filter(TransactionParking.ticket_id == ticket_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")


    tx.receipt_url = f"{BASE_URL}/transactions/receipt/view/{tx.ticket_id}"
    db.commit()  # update database
    return tx

# ---------------- GET LATEST QR CODE ----------------
@router.get("/latest/qr")
def get_latest_qr(ticket_id: str,db: Session = Depends(get_db)):
    """
    Get the latest transaction and return its QR code (PNG),
    pointing to the Azure Blob receipt URL (publicly accessible).
    """
    transaction = db.query(TransactionParking).filter(TransactionParking.ticket_id == ticket_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    tx = transaction

    # ✅ Always regenerate blob receipt if not found or still using VM IP
    if not tx.receipt_url or "blob.core.windows.net" not in tx.receipt_url:
        parking = db.query(Parking).filter(Parking.plate == tx.plate).order_by(Parking.id.desc()).first()
        tx_type = tx.transaction_type.value if tx.transaction_type else "N/A"

        html = f"""
        <html>
            <head>
                <title>Parking E-Receipt</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        margin: 0;
                        padding: 0;
                        background: #f0f0f0;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                    }}
                    .receipt {{
                        background: white;
                        padding: 60px;
                        border-radius: 20px;
                        box-shadow: 0 0 30px rgba(0,0,0,0.2);
                        width: 700px;
                        font-size: 32px;    /* 🔹 Bigger text */
                        line-height: 1.6;
                    }}
                    h2 {{
                        color: #111;
                        text-align: center;
                        font-size: 40px;     /* 🔹 Large heading */
                        margin-bottom: 40px;
                        letter-spacing: 1px;
                    }}
                    p {{
                        margin: 12px 0;
                        font-size: 30px;     /* 🔹 Bigger paragraph text */
                    }}
                    .thankyou {{
                        margin-top: 40px;
                        font-size: 36px;     /* 🔹 Large thank-you message */
                        font-weight: bold;
                        text-align: center;
                        color: #2a7a2a;
                    }}
                    .footer {{
                        margin-top: 40px;
                        font-size: 22px;
                        color: gray;
                        text-align: center;
                    }}
                    .download-btn {{
                        display: block;
                        text-align: center;
                        margin-top: 35px;
                    }}
                    .download-btn a {{
                        text-decoration: none;
                        background-color: #4CAF50;
                        color: white;
                        padding: 20px 50px;
                        font-size: 28px;      /* 🔹 Larger button */
                        border-radius: 10px;
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
                            font-size: 28px;
                            padding: 30px;
                        }}
                        .download-btn {{ display: none; }}
                    }}
                </style>
            </head>
            <body>
                <div class="receipt">
                    <h2>Parking E-Receipt</h2>
                    <p><b>Ticket ID:</b> {transaction.ticket_id}</p>
                    <p><b>Plate:</b> {transaction.plate}</p>
                    <p><b>Time Purchased (Hours):</b> {transaction.hours}</p>
                    <p><b>Time In:</b> {parking.timein if parking else "N/A"}</p>
                    <p><b>Time Out:</b> {parking.timeout if parking else "N/A"}</p>
                    <p><b>Amount:</b> 
                        <span style="font-size:38px; font-weight:bold; color:#000;">
                            RM {transaction.amount:.2f}
                        </span>
                    </p>
                    <p><b>Transaction Type:</b> {tx_type}</p>
        
                    <div class="thankyou">Thank you! Drive safely </div>
        
                    <div class="download-btn">
                        <a href="/transactions/receipt/pdf/{transaction.ticket_id}" target="_blank">
                            Download PDF
                        </a>
                    </div>
        
                    <div class="footer">Generated by Parking System</div>
                </div>
            </body>
        </html>
        """
        html_bytes = html.encode("utf-8")
        filename = f"receipt_{tx.ticket_id}.html"
        html_url = upload_to_blob(filename, html_bytes, content_type="text/html")

        tx.receipt_url = html_url
        db.commit()
        print(f"✅ Uploaded to Azure Blob: {html_url}")
    else:
        print(f"ℹ️ Using existing blob URL: {tx.receipt_url}")

    # Generate QR for Blob URL
    receipt_url = tx.receipt_url
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(receipt_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")




# ---------------- LATEST RECEIPT BY PLATE ----------------
@router.get("/latest/{plate}")
def get_latest_receipt_by_plate(plate: str, db: Session = Depends(get_db)):
    """
    Endpoint to fetch the latest receipt info for a given vehicle plate.
    """

    # 🔹 Step 1: Get the latest transaction for this plate
    transaction = (
        db.query(TransactionParking)
        .filter(TransactionParking.plate == plate)
        .order_by(TransactionParking.id.desc())
        .first()
    )

    if not transaction:
        raise HTTPException(status_code=404, detail="No transaction found for this plate")

    # 🔹 Step 2: Get the latest parking record for this plate (for time in/out)
    parking = (
        db.query(Parking)
        .filter(Parking.plate == plate)
        .order_by(Parking.id.desc())
        .first()
    )

    # 🔹 Step 3: Return combined info
    return {
        "ticket_id": transaction.ticket_id,
        "plate": transaction.plate,
        "hours": transaction.hours,
        "amount": transaction.amount,
        "transaction_type": transaction.transaction_type,
        "time_in": parking.timein if parking else None,
        "time_out": parking.timeout if parking else None,
    }
