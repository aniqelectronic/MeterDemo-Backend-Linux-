from fastapi import APIRouter, Depends, HTTPException 
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session
from datetime import timedelta
from app.db.database import get_db
from app.schema.parking.parking_schema import Parking, PaymentStatusEnum
# from app.utils.Malaysia_time import malaysia_now
from app.utils.sirim_time import sirim_now_naive
from app.schema.parking.transaction_parking_schema import TransactionParking, TicketOverviewEnum
from app.models.parking.parking_model import (
    ParkingCheck,
    ParkingCreate,
    ParkingExtend,
    ParkingResponse
)

import re

from sqlalchemy import func

import qrcode
from io import BytesIO

from app.utils.blob_upload import upload_to_blob

# ----------------- CONFIG -----------------
from app.utils.config import BASE_URL, RATE_PER_HOUR

router = APIRouter(prefix="/parking", tags=["Parking"])

def calculate_amount(hours: float) -> float:
    """Convert parking hours into RM amount."""
    return round(hours * RATE_PER_HOUR, 2)


def clean_terminal_id(terminal: str) -> str:
    """
    Clean terminal ID before placing it inside the ticket ID.

    Examples:
        "TIP 01" -> "TIP01"
        "tip-01" -> "TIP-01"
        "TIP_01" -> "TIP_01"
    """
    cleaned_terminal = re.sub(
        r"[^A-Za-z0-9_-]",
        "",
        terminal.strip(),
    ).upper()

    return cleaned_terminal or "UNKNOWN"


def generate_ticket_id(
    db: Session,
    terminal: str,
    current_time=None,
) -> str:
    """
    Ticket format:

    P-YYYYMMDD-HHMMSS-TERMINAL-DAILYNUMBER

    Daily number is separate for each terminal.

    Examples:
        P-20260710-103000-TIP01-01
        P-20260710-103500-TIP01-02
        P-20260710-104000-TIP02-01
    """

    # SIRIM time is the first priority.
    now = current_time or sirim_now_naive()

    date_part = now.strftime("%Y%m%d")
    time_part = now.strftime("%H%M%S")
    terminal_part = clean_terminal_id(terminal)

    # Match tickets for this date and this exact terminal.
    ticket_pattern = (
        f"P-{date_part}-%-{terminal_part}-%"
    )

    terminal_daily_count = (
        db.query(func.count(TransactionParking.id))
        .filter(
            TransactionParking.terminal == terminal_part,
            TransactionParking.ticket_id.like(ticket_pattern),
        )
        .scalar()
        or 0
    )

    next_daily_number = terminal_daily_count + 1
    sequence_part = f"{next_daily_number:02d}"

    return (
        f"P-{date_part}-"
        f"{time_part}-"
        f"{terminal_part}-"
        f"{sequence_part}"
    )




def get_latest_paid(db: Session, plate: str):
    return (
        db.query(Parking)
        .filter(Parking.plate == plate, Parking.payment_status == PaymentStatusEnum.yes)  
        .order_by(Parking.timeout.desc())
        .first()
    )


def check_active_parking(db: Session, plate: str):
    now = sirim_now_naive()
    latest = get_latest_paid(db, plate)
    if latest and now < latest.timeout:
        return latest
    return None



def add_new_parking(
    db: Session,
    plate: str,
    time_used: float,
    terminal: str,
    transaction_type: str,
    order_no: str = None,
    bank_trx_no: str = None,
):
    now = sirim_now_naive()
    timeout = now + timedelta(hours=time_used)
    amount = calculate_amount(time_used)

    # Clean the terminal ID received from the frontend.
    cleaned_terminal = clean_terminal_id(terminal)

    new_parking = Parking(
        plate=plate,
        terminal=cleaned_terminal,
        time_used=time_used,
        timein=now,
        timeout=timeout,
        payment_status=PaymentStatusEnum.yes,
        amount=amount,
    )

    db.add(new_parking)
    db.commit()
    db.refresh(new_parking)

    next_ticket = generate_ticket_id(
        db=db,
        terminal=cleaned_terminal,
        current_time=now,
    )

    transaction = TransactionParking(
        ticket_id=next_ticket,
        plate=plate,
        terminal=cleaned_terminal,
        hours=time_used,
        amount=amount,
        transaction_type=transaction_type,
        Ticket_Overview=TicketOverviewEnum.new,
        order_no=order_no,
        bank_trx_no=bank_trx_no,
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return new_parking

def extend_parking(
    db: Session,
    plate: str,
    hours: float,
    terminal: str,
    transaction_type: str,
    order_no: str = None,
    bank_trx_no: str = None,
):
    active = check_active_parking(db, plate)

    # If parking is expired, create it as a new parking transaction.
    if not active:
        return add_new_parking(
            db=db,
            plate=plate,
            time_used=hours,
            terminal=terminal,
            transaction_type=transaction_type,
            order_no=order_no,
            bank_trx_no=bank_trx_no,
        )

    now = sirim_now_naive()

    # Clean the terminal ID received from the frontend.
    cleaned_terminal = clean_terminal_id(terminal)

    active.time_used += hours
    active.timeout += timedelta(hours=hours)
    active.amount = calculate_amount(active.time_used)
    active.terminal = cleaned_terminal

    db.commit()
    db.refresh(active)

    next_ticket = generate_ticket_id(
        db=db,
        terminal=cleaned_terminal,
        current_time=now,
    )

    transaction = TransactionParking(
        ticket_id=next_ticket,
        terminal=cleaned_terminal,
        plate=plate,
        hours=hours,
        amount=calculate_amount(hours),
        transaction_type=transaction_type,
        Ticket_Overview=TicketOverviewEnum.extend,
        order_no=order_no,
        bank_trx_no=bank_trx_no,
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
    return add_new_parking(db, parking.plate, parking.time_used, parking.terminal, parking.transaction_type,parking.order_no,parking.bank_trx_no,)  

# ✅ changed path param name from parking_id -> plate
@router.put("/{plate}/{terminal}/extend", response_model=ParkingResponse)
def extend(plate: str, terminal: str, extend: ParkingExtend, db: Session = Depends(get_db)):
    """
    Extend an active paid parking.
    """
    return extend_parking(db, plate, extend.extend_hours, terminal, extend.transaction_type, extend.order_no, extend.bank_trx_no)

@router.get("/", response_model=list[ParkingResponse])
def get_all(db: Session = Depends(get_db)):
    """
    Get all parking records.
    """
    return get_all_parkings(db)


@router.get("/html/qrdummy/{plate}/{hours}/{terminal}/{transaction_type}", response_class=HTMLResponse)
def qr_page(plate: str, hours: int, terminal: str, transaction_type: str):
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
                    body: JSON.stringify({{ plate: '{plate}', time_used: {hours}, terminal: '{terminal}', transaction_type:'{transaction_type}' }})
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

@router.get("/qrdummy/{plate}/{hours}/{terminal}/{transaction_type}")
def generate_receipt_qr(plate: str, hours: int, terminal: str, transaction_type: str):

    # Use stored URL or generate if missing
    receipt_url =  f"{BASE_URL}/parking/html/qrdummy/{plate}/{hours}/{terminal}/{transaction_type}"

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