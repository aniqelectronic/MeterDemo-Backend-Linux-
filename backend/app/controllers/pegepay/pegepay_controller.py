from fastapi import APIRouter, HTTPException, Depends
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
    
    # Always generate a new order number
    last_order = db.query(PegepayOrder).order_by(PegepayOrder.id.desc()).first()
    next_no = f"KN{(last_order.id + 1) if last_order else 1:03d}"


    payload = {
        "order_output": "online",
        "image_file_format": "png",
        "order_no": next_no,
        "override_existing_unprocessed_order_no": "yes",
        "order_amount": str(body.order_amount),
        "qr_validity": str(body.qr_validity),
        "store_id": body.store_id,
        "terminal_id": body.terminal_id,
        "shift_id": body.shift_id
    }

    access_token = get_pegepay_token(db)
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    response = requests.post(PEPAY_ORDER_URL, json=payload, headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    res_data = response.json()
    iframe_url = res_data.get("content", {}).get("iframe_url")
    if not iframe_url:
        raise HTTPException(status_code=500, detail="iframe_url not found in Pegepay response")

    if last_order and last_order.order_no == next_no:
        last_order.order_amount = body.order_amount
        last_order.order_status = "unprocessed"
        db.commit()
        db.refresh(last_order)
    else:
        new_order = PegepayOrder(
            order_no=next_no,
            order_amount=body.order_amount,
            order_status="unprocessed",
            store_id=body.store_id,
            terminal_id=body.terminal_id
        )
        db.add(new_order)
        db.commit()
        db.refresh(new_order)

    return {"iframe_url": iframe_url, "order_no": next_no}


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

    if order_status != "successful":
        return {"message": f"Payment not successful yet (current status: {order_status})", "order_status": order_status}

    order = db.query(PegepayOrder).filter_by(order_no=body.order_no).first()
    if order:
        order.order_status = order_status
        order.order_amount = content.get("order_amount")
        order.store_id = content.get("store_id")
        order.terminal_id = content.get("terminal_id")
        db.commit()
        db.refresh(order)

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