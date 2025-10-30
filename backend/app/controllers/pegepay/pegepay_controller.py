from fastapi import APIRouter, HTTPException, Depends
import requests
from app.models.pegepay.pegepay_model import OrderCreateRequest,OrderStatusRequest
from sqlalchemy.orm import Session
import requests
from app.db.database import get_db
from app.schema.pegepay.pegepay_schema import PegepayOrder
from app.utils.config import refresh_token


router = APIRouter(prefix="/pegepay", tags=["Pegepay"])
PEPAY_TOKEN_URL = "https://pegepay.com/api/get-access-token"
PEPAY_ORDER_URL = "https://pegepay.com/api/npd-wa/order-create/custom-validity"
PEPAY_STATUS_URL = "https://pegepay.com/api/pos/transaction-details"

def refresh_pegepay_token():
    """
    Refresh Pegepay access token using refresh_token.
    Returns only the access_token value.
    """
    try:
        headers = {"Content-Type": "application/json"}
        payload = {"refresh_token": refresh_token}

        response = requests.post(PEPAY_TOKEN_URL, json=payload, headers=headers)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        data = response.json()
        access_token = data.get("access_token")

        if not access_token:
            raise HTTPException(status_code=500, detail="Access token not found in Pegepay response")

        return access_token

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------- Create Order ----------------------
@router.post("/create-order")
def create_order(body: OrderCreateRequest, db: Session = Depends(get_db)):
    # Generate new order_no
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

    access_token = refresh_pegepay_token()
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    response = requests.post(PEPAY_ORDER_URL, json=payload, headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    res_data = response.json()

     # Extract iframe_url
    iframe_url = res_data.get("content", {}).get("iframe_url")
    if not iframe_url:
        raise HTTPException(status_code=500, detail="iframe_url not found in Pegepay response")

    # Save order in DB
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

    # Return only the iframe URL and next_no
    return {"iframe_url": iframe_url,"order_no": next_no}
    

@router.post("/check-status")
def check_order_status(body: OrderStatusRequest, db: Session = Depends(get_db)):
    access_token = refresh_pegepay_token()
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {"order_no": body.order_no}

    response = requests.post(PEPAY_STATUS_URL, json=payload, headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    data = response.json()
    if data.get("order_status") != "successful":
        raise HTTPException(status_code=400, detail="Payment is Not Successfull Yet")

    content = data["content"]

    # Update DB if successful payment
    order = db.query(PegepayOrder).filter_by(order_no=body.order_no).first()
    if order:
        order.order_status = content["order_status"]
        db.commit()

    return {"order_status": content.get("order_status")}
