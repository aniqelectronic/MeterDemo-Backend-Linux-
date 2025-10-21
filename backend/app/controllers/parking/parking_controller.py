from fastapi import APIRouter, Depends, HTTPException 
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session
from datetime import timedelta
from app.db.database import get_db
from app.schema.parking.parking_schema import Parking, PaymentStatusEnum
from app.utils.Malaysia_time import malaysia_now
from app.schema.parking.transaction_parking_schema import TransactionParking, TransactionTypeEnum
from app.models.parking.parking_model import (
    ParkingCheck,
    ParkingCreate,
    ParkingExtend,
    ParkingResponse
)


import qrcode
from io import BytesIO

from app.utils.blob_upload import upload_to_blob

# ----------------- CONFIG -----------------
from app.utils.config import BASE_URL, RATE_PER_HOUR

router = APIRouter(prefix="/parking", tags=["Parking"])


def calculate_amount(hours: float) -> float:  
    """Convert parking hours into RM amount."""
    return round(hours * RATE_PER_HOUR, 2)

# -------------------------
# CRUD Logic
# -------------------------


def get_latest_paid(db: Session, plate: str):
    return (
        db.query(Parking)
        .filter(Parking.plate == plate, Parking.payment_status == PaymentStatusEnum.yes)  
        .order_by(Parking.timeout.desc())
        .first()
    )


def check_active_parking(db: Session, plate: str):
    now = malaysia_now()
    latest = get_latest_paid(db, plate)
    if latest and now < latest.timeout:
        return latest
    return None


def add_new_parking(db: Session, plate: str, time_used: float, terminal: str):
    now = malaysia_now()
    timeout = now + timedelta(hours=time_used)
    amount=calculate_amount(time_used) 
    
    new_parking = Parking(
        plate=plate, 
        terminal= terminal,
        time_used=time_used,
        timein=now,
        timeout=timeout,
        payment_status=PaymentStatusEnum.yes,
        amount=amount,
    )
    db.add(new_parking)
    db.commit()
    db.refresh(new_parking)
    
    # ✅ Add transaction
    last_tx = db.query(TransactionParking).order_by(TransactionParking.id.desc()).first()
    next_ticket = f"P-{(last_tx.id + 1) if last_tx else 1:04d}"
    transaction = TransactionParking(
        ticket_id=next_ticket,
        plate=plate,
        terminal= terminal,
        hours=time_used,
        amount=amount,
        transaction_type=TransactionTypeEnum.new
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return new_parking

# ✅ changed parking_id -> plate
def extend_parking(db: Session, plate: str, hours: float, terminal: str):
    active = check_active_parking(db, plate)
    if not active:
        raise HTTPException(status_code=404, detail="No active paid parking to extend")

    # Maintain timein, update timeout and time_used
    active.time_used += hours
    active.timeout += timedelta(hours=hours)
    active.amount = calculate_amount(active.time_used)
    active.terminal = terminal 
    db.commit()
    db.refresh(active)

    # ✅ Add transaction
    last_tx = db.query(TransactionParking).order_by(TransactionParking.id.desc()).first()
    next_ticket = f"P-{(last_tx.id + 1) if last_tx else 1:04d}"
    transaction = TransactionParking(
        ticket_id=next_ticket,
        terminal=terminal,
        plate=plate,
        hours=hours,
        amount=calculate_amount(hours),
        transaction_type=TransactionTypeEnum.extend
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return active

def get_all_parkings(db: Session):
    return db.query(Parking).all()

# -------------------------
# Endpoints
# -------------------------

@router.post("/check", response_model=ParkingResponse)
def check_parking(parking: ParkingCheck, db: Session = Depends(get_db)):
    """
    Check if plate exists and is active (within timeout).
    """
    active = check_active_parking(db, parking.plate)  
    if active:
        return active
    raise HTTPException(status_code=404, detail="Plate not active or new, proceed to payment")

# New GET endpoint (easier for Java)
@router.get("/check/{plate}", response_model=ParkingResponse)
def check_parking_by_plate(plate: str, db: Session = Depends(get_db)):
    """
    Check parking by plate number directly in path.
    """
    active = check_active_parking(db, plate)
    if active:
        return active
    raise HTTPException(status_code=404, detail="Plate not active or new, proceed to payment")

@router.post("/pay", response_model=ParkingResponse)
def pay_parking(parking: ParkingCreate, db: Session = Depends(get_db)):
    """
    Pay for new parking. Will create new record only if no active paid parking exists.
    """
    active = check_active_parking(db, parking.plate)  
    if active:
        raise HTTPException(status_code=400, detail=f"Parking already active until {active.timeout}")
    return add_new_parking(db, parking.plate, parking.time_used, parking.terminal)  

# ✅ changed path param name from parking_id -> plate
@router.put("/{plate}/{terminal}/extend", response_model=ParkingResponse)
def extend(plate: str, terminal: str, extend: ParkingExtend, db: Session = Depends(get_db)):
    """
    Extend an active paid parking.
    """
    return extend_parking(db, plate, extend.extend_hours, terminal)  

@router.get("/", response_model=list[ParkingResponse])
def get_all(db: Session = Depends(get_db)):
    """
    Get all parking records.
    """
    return get_all_parkings(db)


@router.get("/html/qrdummy/{plate}/{hours}/{terminal}", response_class=HTMLResponse)
def qr_page(plate: str, hours: int, terminal: str):
    # HTML page that will be uploaded to blob
    return f"""
    <html>
    <body style='text-align:center;margin-top:200px;'>
        <h1>Parking Payment</h1>
        <p>Plate: {plate}</p>
        <button style='font-size:30px;padding:20px;'
            onclick="
                fetch('/parking/pay/', {{
                    method:'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ plate: '{plate}', time_used: {hours}, terminal: {terminal} }})
                }})
                .then(response => {{
                    if(response.ok) {{
                        alert('Payment Successful!');
                    }} else {{
                        alert('Payment failed: ' + response.statusText);
                    }}
                }})
                .catch(error => {{
                    alert('Error: ' + error);
                }});
            "
        >
            PAY
        </button>
    </body>
    </html>
    """


# ---------------- Create dummy qr code payment image ----------------

@router.get("/qrdummy/{plate}/{hours}/{terminal}")
def generate_receipt_qr(plate: str, hours: int, terminal: str):

    # Use stored URL or generate if missing
    receipt_url =  f"{BASE_URL}/parking/html/qrdummy/{plate}/{hours}/{terminal}"

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