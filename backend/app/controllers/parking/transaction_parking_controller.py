# app/controllers/transaction_parking_controller.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, cast , Integer
from fastapi.responses import HTMLResponse, FileResponse , StreamingResponse, JSONResponse
from app.db.database import get_db
from app.schema.parking.transaction_parking_schema import TransactionParking
from app.models.parking.transaction_parking_model import TransactionResponse
from app.utils.blob_upload import upload_to_blob
from app.controllers.parking.parking_receipt import generate_parking_receipt
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
    return transactions


# ---------------- RECEIPT (HTML PAGE) ----------------
@router.get("/receipt/view/{ticket_id}", response_class=HTMLResponse)
def view_receipt(ticket_id: str, db: Session = Depends(get_db)):

    transaction = (
        db.query(TransactionParking)
        .filter(TransactionParking.ticket_id == ticket_id)
        .first()
    )
    if not transaction:
        raise HTTPException(status_code=404, detail="Ticket not found")

    parking = (
        db.query(Parking)
        .filter(Parking.plate == transaction.plate)
        .order_by(Parking.id.desc())
        .first()
    )


    db.expunge_all()
    db.close()
    
    #base_dir = os.path.dirname(os.path.abspath(__file__))
    #logo_path = os.path.abspath(os.path.join(base_dir, "../../resources/images/PBT_Kuantan_logo.png"))
    
    pdf_bytes = generate_parking_receipt(
        ticket_id=transaction.ticket_id,
        plate=transaction.plate,
        hours=transaction.hours,
        time_in=parking.timein if parking else "N/A",
        time_out=parking.timeout if parking else "N/A",
        amount=transaction.amount,
        transaction_type= transaction.transaction_type if transaction else "N/A",
        #logo_bytes=LOGO_BYTES
        #logo_path=logo_path
    )

    pdf_filename = f"receipt_{transaction.ticket_id}.pdf"
    pdf_url = upload_to_blob(pdf_filename, pdf_bytes, content_type="application/pdf")

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
                <p><b>Transaction Type:</b> {transaction.transaction_type if transaction else "N/A"}</p>
    
                <div class="thankyou">Thank you! Drive safely </div>
    
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
    filename = f"receipt_{transaction.ticket_id}.html"
    html_url = upload_to_blob(filename, html_bytes, content_type="text/html")

    # Generate QR for Blob URL
    receipt_url = html_url
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(receipt_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")

# ---------------- RECEIPT PDF ----------------
from fastapi.responses import StreamingResponse
import io
from fpdf import FPDF

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

    return tx

# ---------------- GET LATEST QR CODE ----------------
@router.get("/latest/qr")
def get_latest_qr(db: Session = Depends(get_db)):
    """
    Get the latest transaction and return its QR code (PNG),
    pointing to the Azure Blob receipt URL (publicly accessible).
    """
    tx = db.query(TransactionParking).order_by(TransactionParking.id.desc()).first()
    if not tx:
        raise HTTPException(status_code=404, detail="No transactions found")

    parking = (
        db.query(Parking)
        .filter(Parking.plate == tx.plate)
        .order_by(Parking.id.desc())
        .first()
    )

    db.expunge_all()
    db.close()

    #base_dir = os.path.dirname(os.path.abspath(__file__))
    #logo_path = os.path.abspath(os.path.join(base_dir, "../../resources/images/PBT_Kuantan_logo.png"))
        
    pdf_bytes = generate_parking_receipt(
            ticket_id=tx.ticket_id,
            plate=tx.plate,
            hours=tx.hours,
            time_in=parking.timein if parking else "N/A",
            time_out=parking.timeout if parking else "N/A",
            amount=tx.amount,
            transaction_type= tx.transaction_type if tx else "N/A",
            #logo_bytes=LOGO_BYTES
            #logo_path=logo_path
        )

        # ✅ Upload the PDF to Azure Blob
    pdf_filename = f"receipt_{tx.ticket_id}.pdf"
    pdf_url = upload_to_blob(pdf_filename, pdf_bytes, content_type="application/pdf")
        
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
                    <p><b>Ticket ID:</b> {tx.ticket_id}</p>
                    <p><b>Plate:</b> {tx.plate}</p>
                    <p><b>Time Purchased (Hours):</b> {tx.hours}</p>
                    <p><b>Time In:</b> {parking.timein if parking else "N/A"}</p>
                    <p><b>Time Out:</b> {parking.timeout if parking else "N/A"}</p>
                    <p><b>Amount:</b> 
                        <span style="font-size:38px; font-weight:bold; color:#000;">
                            RM {tx.amount:.2f}
                        </span>
                    </p>
                    <p><b>Transaction Type:</b> {tx.transaction_type if tx else "N/A"}</p>
        
                    <div class="thankyou">Thank you! Drive safely </div>
        
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
    filename = f"receipt_{tx.ticket_id}.html"
    html_url = upload_to_blob(filename, html_bytes, content_type="text/html")

    # Generate QR for Blob URL
    receipt_url = html_url
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
        "terminal": transaction.terminal,
        "plate": transaction.plate,
        "hours": transaction.hours,
        "amount": transaction.amount,
        "transaction_type": transaction.transaction_type,
        "time_in": parking.timein if parking else None,
        "time_out": parking.timeout if parking else None,
    }
