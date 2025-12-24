from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import HTMLResponse
import requests, time
from sqlalchemy.orm import Session
from app.models.pegepay.pegepay_model import OrderCreateRequest, OrderStatusRequest
from app.db.database import get_db
from app.schema.pegepay.pegepay_schema import PegepayOrder, PegepayToken
from app.utils.config import refresh_token

router = APIRouter(prefix="/pegepay", tags=["Pegepay"])

PEPAY_TOKEN_URL = "https://pegepay.com/api/get-access-token"
PEPAY_ORDER_URL = "https://pegepay.com/api/npd-wa/order-create/custom-validity"
PEPAY_STATUS_URL = "https://pegepay.com/api/pos/transaction-details"


def get_pegepay_token(db: Session):
    """
    Return a valid Pegepay token (shared via DB).
    Auto-refreshes when expired.
    """
    current_time_ms = int(time.time() * 1000)

    token_entry = db.query(PegepayToken).order_by(PegepayToken.id.desc()).first()

    # ✅ Still valid
    if token_entry and current_time_ms < token_entry.token_expired_at:
        return token_entry.access_token

    # 🔄 Refresh from Pegepay
    headers = {"Content-Type": "application/json"}
    payload = {"refresh_token": refresh_token}

    response = requests.post(PEPAY_TOKEN_URL, json=payload, headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    data = response.json()
    access_token = data.get("access_token")
    token_expired_at = data.get("token_expired_at", 0)

    if not access_token:
        raise HTTPException(status_code=500, detail="Access token not found in Pegepay response")

    # ✅ Save to DB (replace existing)
    if token_entry:
        token_entry.access_token = access_token
        token_entry.token_expired_at = token_expired_at
    else:
        token_entry = PegepayToken(access_token=access_token, token_expired_at=token_expired_at)
        db.add(token_entry)

    db.commit()
    db.refresh(token_entry)

    return access_token


# ---------------------- Create Order ----------------------
@router.post("/create-order")
def create_order(body: OrderCreateRequest, db: Session = Depends(get_db)):
    # ✅ Step 1: Use terminal_id as the code
    terminal_code = body.terminal_id.strip()  # e.g. "KN08"
    terminal_prefix = f"TXN-{terminal_code}-"

    # ✅ Step 2: Check for unprocessed order for this specific terminal_id
    existing_order = (
        db.query(PegepayOrder)
        .filter(PegepayOrder.terminal_id == terminal_code)
        .filter(PegepayOrder.order_status == "unprocessed")
        .order_by(PegepayOrder.id.desc())
        .first()
    )

    if existing_order:
        order_no = existing_order.order_no
        print(f"Reusing unprocessed order: {order_no} for terminal {terminal_code}")
    else:
        # ✅ Step 3: Find last order for this terminal_id
        last_order = (
            db.query(PegepayOrder)
            .filter(PegepayOrder.terminal_id == terminal_code)
            .filter(PegepayOrder.order_no.like(f"{terminal_prefix}%"))
            .order_by(PegepayOrder.id.desc())
            .first()
        )

        if last_order and last_order.order_no.startswith(terminal_prefix):
            try:
                last_number = int(last_order.order_no.split("-")[-1])
            except ValueError:
                last_number = 0
        else:
            last_number = 0

        next_number = last_number + 1

        # ✅ Keep within PegePay 15-character limit
        max_length = 15 - len(terminal_prefix)
        order_no = f"{terminal_prefix}{str(next_number).zfill(max_length)}"[:15]

        print(f"Creating new order: {order_no} for terminal {terminal_code}")

    # ✅ Step 4: Prepare PegePay payload
    payload = {
        "order_output": "online",
        "image_file_format": "png",
        "order_no": order_no,
        "override_existing_unprocessed_order_no": "yes",
        "order_amount": str(body.order_amount),
        "qr_validity": str(body.qr_validity),
        "store_id": body.store_id,
        "terminal_id": terminal_code,  # use the same for API call
        "shift_id": body.shift_id
    }

    # ✅ Step 5: Get valid PegePay token
    access_token = get_pegepay_token(db)
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    response = requests.post(PEPAY_ORDER_URL, json=payload, headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    res_data = response.json()
    iframe_url = res_data.get("content", {}).get("iframe_url")
    if not iframe_url:
        raise HTTPException(status_code=500, detail="iframe_url not found in Pegepay response")

    # ✅ Step 6: Save or update DB
    if existing_order:
        existing_order.order_amount = body.order_amount
        existing_order.order_status = "unprocessed"
        existing_order.store_id = body.store_id
        db.commit()
        db.refresh(existing_order)
    else:
        new_order = PegepayOrder(
            order_no=order_no,
            order_amount=body.order_amount,
            order_status="unprocessed",
            store_id=body.store_id,
            terminal_id=terminal_code
        )
        db.add(new_order)
        db.commit()
        db.refresh(new_order)

    return {"iframe_url": iframe_url, "order_no": order_no}




# ---------------------- Check Status ----------------------
@router.post("/check-status")
def check_order_status(body: OrderStatusRequest, db: Session = Depends(get_db)):
    access_token = get_pegepay_token(db)
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {"order_no": body.order_no}

    response = requests.post(PEPAY_STATUS_URL, json=payload, headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    data = response.json()
    if data.get("status") != "success" or "content" not in data:
        raise HTTPException(status_code=500, detail="Invalid Pegepay response")

    content = data["content"]
    order_status = content.get("order_status")

    # 🟡 If not successful, return directly — no DB update needed
    if order_status != "successful":
        return {
            "order_no": content.get("order_no"),
            "order_status": order_status,
            "message": f"Payment not successful yet (current status: {order_status})"
        }

    # ✅ Only update DB when payment is successful
    db.query(PegepayOrder).filter_by(order_no=body.order_no).update({
        PegepayOrder.order_status: order_status,
        PegepayOrder.order_amount: content.get("order_amount"),
        PegepayOrder.store_id: content.get("store_id"),
        PegepayOrder.terminal_id: content.get("terminal_id"),
    })
    db.commit()

    return {
        "order_no": content.get("order_no"),
        "order_status": order_status,
        "bank_trx_no": content.get("bank_trx_no")
    }

# ---------------------- Get All Orders ----------------------
@router.get("/get-all-orders")
def get_all_orders(db: Session = Depends(get_db)):
    orders = db.query(PegepayOrder).all()
    return [
        {
            "id": o.id,
            "order_no": o.order_no,
            "order_amount": o.order_amount,
            "order_status": o.order_status,
            "store_id": o.store_id,
            "terminal_id": o.terminal_id
        }
        for o in orders
    ]
    
@router.get("/iframe-wrapper", response_class=HTMLResponse)
def iframe_wrapper(iframe_url: str):
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>PegePay QR Payment</title>
        <style>
            body {{
                margin: 0;
                background: #ffffff;
                font-family: Arial, sans-serif;
                display: flex;
                flex-direction: column;
                align-items: center;
            }}

            iframe {{
                width: 1080px;
                height: 1400px;
                border: none;
                transform: scale(1.5);    /* zoom 1.5x */
                transform-origin: top left; /* make it zoom from top-left corner */
            }}

            .button-container {{
                margin-top: 30px;
                margin-bottom: 30px;
            }}

            button {{
                width: 400px;        /* 👈 smaller width */
                height: 80px;        /* 👈 smaller height */
                font-size: 28px;
                font-weight: bold;
                color: white;
                background-color: red;
                border: none;
                border-radius: 10px;
                cursor: pointer;
            }}

            button:active {{
                background-color: darkred;
            }}
        </style>
    </head>
    <body>
        <iframe src="{iframe_url}" allowfullscreen></iframe>

        <div class="button-container">
            <button onclick="cancelPayment()">Batal / Cancel</button>
        </div>

        <script>
    function cancelPayment() {{
        // ❌ window.close() won't work
        if (window.flutter_inappwebview) {{
            // for webview_flutter, optional
        }}
        // Send message to Flutter via custom URL scheme
        window.location.href = "app://cancelPayment";
    }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)