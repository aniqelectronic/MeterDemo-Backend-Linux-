import re
import requests
import time

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.pegepay.pegepay_model import (
    OrderCreateRequest,
    OrderStatusRequest,
)
from app.db.database import get_db
from app.schema.pegepay.pegepay_schema import (
    PegepayOrder,
    PegepayToken,
)
from app.utils.config import refresh_token
from app.utils.sirim_time import sirim_now_naive


router = APIRouter(
    prefix="/pegepay",
    tags=["Pegepay"],
)


PEPAY_TOKEN_URL = "https://pegepay.com/api/get-access-token"
PEPAY_ORDER_URL = (
    "https://pegepay.com/api/npd-wa/"
    "order-create/custom-validity"
)
PEPAY_STATUS_URL = (
    "https://pegepay.com/api/pos/"
    "transaction-details"
)


# =========================================================
# TERMINAL ID
# =========================================================

def clean_terminal_id(terminal_id: str) -> str:
    """
    Clean the terminal ID for use inside the PegePay order number.

    The order-number terminal code is limited to four characters
    so the complete order number remains below PegePay's
    15-character limit.

    Examples:
        KN08  -> KN08
        kn08  -> KN08
        KN 08 -> KN08
        TIP01 -> TIP0

    Important:
        If the actual PegePay terminal ID contains more than four
        characters, keep the actual terminal ID separately for the
        PegePay API payload.
    """

    cleaned = re.sub(
        r"[^A-Za-z0-9]",
        "",
        terminal_id.strip(),
    ).upper()

    if not cleaned:
        cleaned = "UNKN"

    return cleaned[:4]


def clean_actual_terminal_id(terminal_id: str) -> str:
    """
    Clean the complete terminal ID received from the frontend.

    Unlike clean_terminal_id(), this function does not shorten
    the terminal ID. It is used for the actual PegePay API request.
    """

    cleaned = re.sub(
        r"[^A-Za-z0-9_-]",
        "",
        terminal_id.strip(),
    ).upper()

    if not cleaned:
        raise HTTPException(
            status_code=400,
            detail="Terminal ID is required",
        )

    return cleaned


# =========================================================
# ORDER NUMBER GENERATOR
# =========================================================

def generate_pegepay_order_no(
    db: Session,
    terminal_id: str,
    current_time=None,
) -> str:
    """
    Generate a PegePay order number.

    Format:
        TTTTDDMMYYCCCC

    Example:
        KN081007260001

    Breakdown:
        KN08   = terminal code
        100726 = 10 July 2026
        0001   = first order for that terminal on that day

    Rules:
        - Uses SIRIM time as the first priority.
        - Counter is separate for each terminal.
        - Counter resets automatically when the SIRIM date changes.
        - Supports 0001 until 9999.
        - Maximum generated length is 14 characters.
        - PegePay maximum allowed length is 15 characters.
    """

    # Use the supplied SIRIM time or retrieve it now.
    now = current_time or sirim_now_naive()

    terminal_code = clean_terminal_id(terminal_id)

    # DDMMYY based on SIRIM time.
    date_part = now.strftime("%d%m%y")

    # Example: KN08100726
    prefix = f"{terminal_code}{date_part}"

    # Count only orders belonging to:
    # 1. The same terminal code
    # 2. The same SIRIM date
    daily_count = (
        db.query(func.count(PegepayOrder.id))
        .filter(
            PegepayOrder.order_no.like(
                f"{prefix}%"
            )
        )
        .scalar()
        or 0
    )

    next_count = daily_count + 1

    if next_count > 9999:
        raise HTTPException(
            status_code=500,
            detail=(
                "Daily PegePay order limit exceeded "
                f"for terminal {terminal_code}"
            ),
        )

    order_no = f"{prefix}{next_count:04d}"

    # PegePay only allows a maximum of 15 characters.
    if len(order_no) > 15:
        raise HTTPException(
            status_code=500,
            detail=(
                "Generated PegePay order number is too long: "
                f"{order_no}"
            ),
        )

    return order_no


def generate_retry_order_no(
    db: Session,
    terminal_id: str,
    previous_order_no: str,
    existing_order: PegepayOrder | None,
) -> str:
    """
    Generate a different order number for a PegePay retry.

    If an existing order is already stored in MySQL, the normal
    database counter can generate the next number.

    If the first generated order has not yet been stored, manually
    increase the final four-digit counter to prevent retrying with
    the same order number.
    """

    retry_sirim_time = sirim_now_naive()

    if existing_order is not None:
        return generate_pegepay_order_no(
            db=db,
            terminal_id=terminal_id,
            current_time=retry_sirim_time,
        )

    # The first generated order was not saved in MySQL.
    # Increase its final four digits manually.
    if len(previous_order_no) < 4:
        raise HTTPException(
            status_code=500,
            detail="Invalid previous PegePay order number",
        )

    try:
        current_count = int(previous_order_no[-4:])
    except ValueError as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to read PegePay order counter from "
                f"{previous_order_no}"
            ),
        ) from error

    next_count = current_count + 1

    if next_count > 9999:
        raise HTTPException(
            status_code=500,
            detail=(
                "Daily PegePay order limit exceeded "
                f"for terminal {terminal_id}"
            ),
        )

    order_prefix = previous_order_no[:-4]
    retry_order_no = (
        f"{order_prefix}{next_count:04d}"
    )

    if len(retry_order_no) > 15:
        raise HTTPException(
            status_code=500,
            detail=(
                "Generated retry order number is too long: "
                f"{retry_order_no}"
            ),
        )

    return retry_order_no


# =========================================================
# PEGE PAY TOKEN
# =========================================================

def get_pegepay_token(db: Session):
    """
    Return a valid PegePay access token.

    The token is shared through MySQL and refreshed automatically
    when it has expired.
    """

    current_time_ms = int(time.time() * 1000)

    token_entry = (
        db.query(PegepayToken)
        .order_by(PegepayToken.id.desc())
        .first()
    )

    # Existing token is still valid.
    if (
        token_entry
        and current_time_ms
        < token_entry.token_expired_at
    ):
        return token_entry.access_token

    headers = {
        "Content-Type": "application/json",
    }

    payload = {
        "refresh_token": refresh_token,
    }

    try:
        response = requests.post(
            PEPAY_TOKEN_URL,
            json=payload,
            headers=headers,
            timeout=20,
        )
    except requests.RequestException as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "Unable to connect to PegePay token service: "
                f"{error}"
            ),
        ) from error

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text,
        )

    data = response.json()

    access_token = data.get("access_token")
    token_expired_at = data.get(
        "token_expired_at",
        0,
    )

    if not access_token:
        raise HTTPException(
            status_code=500,
            detail=(
                "Access token was not found in "
                "the PegePay response"
            ),
        )

    if token_entry:
        token_entry.access_token = access_token
        token_entry.token_expired_at = (
            token_expired_at
        )
    else:
        token_entry = PegepayToken(
            access_token=access_token,
            token_expired_at=token_expired_at,
        )
        db.add(token_entry)

    db.commit()
    db.refresh(token_entry)

    return access_token


# =========================================================
# QR GUIDE IMAGE
# =========================================================

@router.get("/qr-guide")
def qr_guide():
    return FileResponse(
        "app/resources/images/qr_guide2.png",
        media_type="image/png",
    )


# =========================================================
# CREATE PEGE PAY ORDER
# =========================================================

@router.post("/create-order")
def create_order(
    body: OrderCreateRequest,
    db: Session = Depends(get_db),
):
    """
    Create or reuse a PegePay QR payment order.

    Order-number format:
        TTTTDDMMYYCCCC

    Example:
        KN081007260001

    The order number:
        - Uses SIRIM time
        - Resets the sequence each new day
        - Has a separate sequence for each terminal
        - Supports up to 9,999 orders per terminal per day
    """

    # Complete terminal ID for PegePay API.
    actual_terminal_id = clean_actual_terminal_id(
        body.terminal_id
    )

    # Four-character terminal code for order number.
    terminal_code = clean_terminal_id(
        actual_terminal_id
    )

    # Use SIRIM time once for this request.
    current_sirim_time = sirim_now_naive()

    # DDMMYY from SIRIM time.
    date_part = current_sirim_time.strftime(
        "%d%m%y"
    )

    # Example: KN08100726
    current_day_prefix = (
        f"{terminal_code}{date_part}"
    )

    # Reuse only an unprocessed order from:
    # 1. The same actual terminal
    # 2. The same SIRIM date
    existing_order = (
        db.query(PegepayOrder)
        .filter(
            PegepayOrder.terminal_id
            == actual_terminal_id,
            PegepayOrder.order_status
            == "unprocessed",
            PegepayOrder.order_no.like(
                f"{current_day_prefix}%"
            ),
        )
        .order_by(PegepayOrder.id.desc())
        .first()
    )

    if existing_order:
        order_no = existing_order.order_no

        print(
            "[PegePay] Reusing today's unprocessed "
            f"order {order_no} for terminal "
            f"{actual_terminal_id}"
        )
    else:
        order_no = generate_pegepay_order_no(
            db=db,
            terminal_id=terminal_code,
            current_time=current_sirim_time,
        )

        print(
            "[PegePay] Creating new order "
            f"{order_no} for terminal "
            f"{actual_terminal_id}"
        )

    payload = {
        "order_output": "online",
        "image_file_format": "png",
        "order_no": order_no,
        "override_existing_unprocessed_order_no": "yes",
        "order_amount": str(body.order_amount),
        "qr_validity": str(body.qr_validity),
        "store_id": body.store_id,
        "terminal_id": actual_terminal_id,
        "shift_id": body.shift_id,
    }

    access_token = get_pegepay_token(db)

    headers = {
        "Authorization": (
            f"Bearer {access_token}"
        ),
        "Content-Type": "application/json",
    }

    # First PegePay request.
    try:
        response = requests.post(
            PEPAY_ORDER_URL,
            json=payload,
            headers=headers,
            timeout=30,
        )
    except requests.RequestException as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "Unable to connect to PegePay "
                f"order service: {error}"
            ),
        ) from error

    # PegePay rejected the first order.
    if response.status_code != 200:
        print(
            "[PegePay] First order was rejected. "
            "Generating a new SIRIM-based order number."
        )

        if existing_order:
            existing_order.order_status = "successful"
            db.commit()

            print(
                "[PegePay] Marked previous order "
                f"{existing_order.order_no} as successful."
            )

        # Generate a different retry order number.
        new_order_no = generate_retry_order_no(
            db=db,
            terminal_id=terminal_code,
            previous_order_no=order_no,
            existing_order=existing_order,
        )

        print(
            "[PegePay] Retrying with new order "
            f"number {new_order_no}"
        )

        payload["order_no"] = new_order_no

        try:
            retry_response = requests.post(
                PEPAY_ORDER_URL,
                json=payload,
                headers=headers,
                timeout=30,
            )
        except requests.RequestException as error:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Unable to connect to PegePay "
                    f"during retry: {error}"
                ),
            ) from error

        if retry_response.status_code != 200:
            raise HTTPException(
                status_code=retry_response.status_code,
                detail=retry_response.text,
            )

        response_data = retry_response.json()

        iframe_url = (
            response_data
            .get("content", {})
            .get("iframe_url")
        )

        order_no = new_order_no

        new_order = PegepayOrder(
            order_no=order_no,
            order_amount=body.order_amount,
            order_status="unprocessed",
            store_id=body.store_id,
            terminal_id=actual_terminal_id,
        )

        db.add(new_order)
        db.commit()
        db.refresh(new_order)

    else:
        response_data = response.json()

        iframe_url = (
            response_data
            .get("content", {})
            .get("iframe_url")
        )

        if existing_order:
            existing_order.order_amount = (
                body.order_amount
            )
            existing_order.store_id = body.store_id
            existing_order.terminal_id = (
                actual_terminal_id
            )
            existing_order.order_status = (
                "unprocessed"
            )

            db.commit()
            db.refresh(existing_order)

        else:
            new_order = PegepayOrder(
                order_no=order_no,
                order_amount=body.order_amount,
                order_status="unprocessed",
                store_id=body.store_id,
                terminal_id=actual_terminal_id,
            )

            db.add(new_order)
            db.commit()
            db.refresh(new_order)

    if not iframe_url:
        raise HTTPException(
            status_code=500,
            detail=(
                "iframe_url is missing from "
                "the PegePay response"
            ),
        )

    return {
        "iframe_url": iframe_url,
        "order_no": order_no,
    }


# =========================================================
# CHECK PAYMENT STATUS
# =========================================================

@router.post("/check-status")
def check_order_status(
    body: OrderStatusRequest,
    db: Session = Depends(get_db),
):
    """
    Check the latest payment status from PegePay.

    The local database is updated only when PegePay reports
    that the payment was successful.
    """

    access_token = get_pegepay_token(db)

    headers = {
        "Authorization": (
            f"Bearer {access_token}"
        ),
        "Content-Type": "application/json",
    }

    payload = {
        "order_no": body.order_no,
    }

    try:
        response = requests.post(
            PEPAY_STATUS_URL,
            json=payload,
            headers=headers,
            timeout=30,
        )
    except requests.RequestException as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "Unable to connect to PegePay "
                f"status service: {error}"
            ),
        ) from error

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text,
        )

    data = response.json()

    if (
        data.get("status") != "success"
        or "content" not in data
    ):
        raise HTTPException(
            status_code=500,
            detail="Invalid PegePay status response",
        )

    content = data["content"]
    order_status = content.get("order_status")

    if order_status != "successful":
        return {
            "order_no": content.get("order_no"),
            "order_status": order_status,
            "message": (
                "Payment is not successful yet "
                f"(current status: {order_status})"
            ),
        }

    db.query(PegepayOrder).filter_by(
        order_no=body.order_no
    ).update(
        {
            PegepayOrder.order_status:
                order_status,
            PegepayOrder.order_amount:
                content.get("order_amount"),
            PegepayOrder.store_id:
                content.get("store_id"),
            PegepayOrder.terminal_id:
                content.get("terminal_id"),
        }
    )

    db.commit()

    return {
        "order_no": content.get("order_no"),
        "order_status": order_status,
        "bank_trx_no": content.get(
            "bank_trx_no"
        ),
    }


# =========================================================
# GET ALL ORDERS
# =========================================================

@router.get("/get-all-orders")
def get_all_orders(
    db: Session = Depends(get_db),
):
    orders = (
        db.query(PegepayOrder)
        .order_by(PegepayOrder.id.desc())
        .all()
    )

    return [
        {
            "id": order.id,
            "order_no": order.order_no,
            "order_amount": order.order_amount,
            "order_status": order.order_status,
            "store_id": order.store_id,
            "terminal_id": order.terminal_id,
        }
        for order in orders
    ]


# =========================================================
# IFRAME WRAPPER
# =========================================================

@router.get(
    "/iframe-wrapper",
    response_class=HTMLResponse,
)
def iframe_wrapper(iframe_url: str):
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">

        <title>PegePay QR Payment</title>

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <style>
            body {{
                margin: 0;
                background: #ffffff;
                font-family: Arial, sans-serif;
                overflow: hidden;
                display: flex;
                flex-direction: column;
                align-items: center;
            }}

            .iframe-container {{
                width: 100vw;
                height: 58vh;
                overflow: hidden;
                display: flex;
                justify-content: center;
                align-items: flex-start;
                background: white;
            }}

            .iframe-container iframe {{
                width: 1080px;
                height: 1700px;
                border: none;

                transform:
                    scale(2.0)
                    translateX(-50%)
                    translateY(-18%);

                transform-origin: top left;
            }}

            .promo-container {{
                position: fixed;
                bottom: 120px;
                left: 50%;
                transform: translateX(-50%);
                z-index: 998;
                width: 80vw;
                text-align: center;
            }}

            .promo-container img {{
                width: 100%;
                max-width: 550px;
                border-radius: 15px;
            }}

            .button-container {{
                position: fixed;
                bottom: 50px;
                left: 50%;
                transform: translateX(-50%);
                z-index: 999;
            }}

            button {{
                width: 300px;
                height: 65px;
                font-size: 22px;
            }}

            button:active {{
                background-color: darkred;
            }}

            .loader {{
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: white;
                display: flex;
                justify-content: center;
                align-items: center;
                flex-direction: column;
                z-index: 99999;
            }}

            .spinner {{
                width: 90px;
                height: 90px;
                border: 10px solid #eeeeee;
                border-top: 10px solid #0359d2;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }}

            .loader-text {{
                margin-top: 20px;
                font-size: 28px;
                font-weight: bold;
                color: #0359d2;
            }}

            @keyframes spin {{
                100% {{
                    transform: rotate(360deg);
                }}
            }}
        </style>
    </head>

    <body>
        <div
            class="loader"
            id="loader"
        >
            <div class="spinner"></div>

            <div class="loader-text">
                Loading QR Payment...
            </div>
        </div>

        <div class="iframe-container">
            <iframe id="qrFrame"></iframe>
        </div>

        <div class="promo-container">
            <img
                src="/pegepay/qr-guide"
                alt="QR Guide"
            >
        </div>

        <div class="button-container">
            <button onclick="cancelPayment()">
                Batal / Cancel
            </button>
        </div>

        <script>
            const iframeUrl = "{iframe_url}";
            const iframe =
                document.getElementById("qrFrame");
            const loader =
                document.getElementById("loader");

            iframe.src = iframeUrl;

            iframe.onload = () => {{
                loader.style.display = "none";
            }};

            setTimeout(() => {{
                document.querySelector(
                    ".loader-text"
                ).innerText =
                    "Still loading QR... please wait";
            }}, 3000);

            function cancelPayment() {{
                window.location.href =
                    "app://cancelPayment";
            }}
        </script>
    </body>
    </html>
    """

    return HTMLResponse(
        content=html_content
    )