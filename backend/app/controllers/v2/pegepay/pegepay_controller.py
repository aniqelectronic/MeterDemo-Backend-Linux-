import re
import requests
import time

from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse
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
    tags=["Pegepay V2"],
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

    The terminal ID is kept exactly as received (after removing
    invalid characters).

    Examples:
        KN08   -> KN08
        TEST01 -> TEST01
        BENT01 -> BENT01

    Maximum supported terminal ID length is 6 characters because
    the PegePay order number cannot exceed 15 characters.
    """

    cleaned = re.sub(
        r"[^A-Za-z0-9]",
        "",
        terminal_id.strip(),
    ).upper()

    if not cleaned:
        cleaned = "UNKN"

    return cleaned


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

    if len(cleaned) > 6:
        raise HTTPException(
            status_code=400,
            detail="Terminal ID must not exceed 6 characters.",
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
        TTTTDDMMYYCCC

    Example:
        KN08100726001

    Breakdown:
        KN08   = terminal code
        100726 = 10 July 2026
        001   = first order for that terminal on that day

    Rules:
        - Uses SIRIM time as the first priority.
        - Counter is separate for each terminal.
        - Counter resets automatically when the SIRIM date changes.
        - Supports 001 until 999.
        - Maximum generated length is 13 characters.
        - PegePay maximum allowed length is 15 characters.
    """

    # Use the supplied SIRIM time or retrieve it now.
    now = current_time or sirim_now_naive()

    terminal_code = clean_terminal_id(terminal_id)

    # DDMMYY based on SIRIM time.
    date_part = now.strftime("%d%m%y")

    # Example: KN08100726
    prefix = f"{terminal_code}{date_part}"

    # Read today's existing order numbers and use the highest
    # three-digit suffix. Counting rows is not safe when a retry
    # skips a number or an older row is missing.
    existing_order_numbers = (
        db.query(PegepayOrder.order_no)
        .filter(
            PegepayOrder.order_no.like(
                f"{prefix}%"
            )
        )
        .all()
    )

    highest_count = 0

    for row in existing_order_numbers:
        existing_order_no = row[0]

        if not existing_order_no:
            continue

        suffix = existing_order_no[len(prefix):]

        if len(suffix) != 3 or not suffix.isdigit():
            continue

        highest_count = max(
            highest_count,
            int(suffix),
        )

    next_count = highest_count + 1

    if next_count > 999:
        raise HTTPException(
            status_code=500,
            detail=(
                "Daily PegePay order limit exceeded "
                f"for terminal {terminal_code}"
            ),
        )

    order_no = f"{prefix}{next_count:03d}"

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
    increase the final three-digit counter to prevent retrying with
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
    # Increase its final three  digits manually.
    if len(previous_order_no) < 3:
        raise HTTPException(
            status_code=500,
            detail="Invalid previous PegePay order number",
        )

    try:
        current_count = int(previous_order_no[-3:])
    except ValueError as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to read PegePay order counter from "
                f"{previous_order_no}"
            ),
        ) from error

    next_count = current_count + 1

    if next_count > 999:
        raise HTTPException(
            status_code=500,
            detail=(
                "Daily PegePay order limit exceeded "
                f"for terminal {terminal_id}"
            ),
        )

    order_prefix = previous_order_no[:-3]
    retry_order_no = (
        f"{order_prefix}{next_count:03d}"
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

def get_pegepay_token(
    db: Session,
    force_refresh: bool = False,
):
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
        not force_refresh
        and
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

    try:
        data = response.json()
    except ValueError as error:
        raise HTTPException(
            status_code=502,
            detail="PegePay token service returned invalid JSON",
        ) from error

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

    try:
        token_expired_at = int(token_expired_at)
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=502,
            detail="PegePay returned an invalid token expiry",
        ) from error

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


def pegepay_post_with_token_retry(
    *,
    db: Session,
    url: str,
    payload: dict,
    timeout: int = 30,
):
    """
    Send an authenticated POST request to PegePay.

    If PegePay rejects the cached bearer token with HTTP 401 or
    403, force-refresh it and retry the original request once.
    """

    def send_request(access_token: str):
        return requests.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=timeout,
        )

    def is_invalid_token_response(response) -> bool:
        """
        PegePay may report an invalid token in two ways:

        1. HTTP status 401 or 403.
        2. HTTP 200 with a JSON body such as:
           {
               "status": "failure",
               "message": "invalid token",
               "code": 403
           }
        """
        if response.status_code in (401, 403):
            return True

        try:
            response_data = response.json()
        except ValueError:
            return False

        if not isinstance(response_data, dict):
            return False

        status = str(
            response_data.get("status", "")
        ).strip().lower()

        message = str(
            response_data.get("message", "")
        ).strip().lower()

        try:
            response_code = int(
                response_data.get("code", 0)
            )
        except (TypeError, ValueError):
            response_code = 0

        return (
            response_code in (401, 403)
            or "invalid token" in message
            or (
                status == "failure"
                and "token" in message
            )
        )

    access_token = get_pegepay_token(db)

    try:
        response = send_request(access_token)
    except requests.RequestException as error:
        raise HTTPException(
            status_code=503,
            detail=f"Unable to connect to PegePay: {error}",
        ) from error

    if not is_invalid_token_response(response):
        return response

    print(
        "[PegePay] Bearer token rejected. "
        "Refreshing and retrying once.",
        flush=True,
    )

    new_access_token = get_pegepay_token(
        db,
        force_refresh=True,
    )

    try:
        retry_response = send_request(new_access_token)
    except requests.RequestException as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "Unable to connect to PegePay after token "
                f"refresh: {error}"
            ),
        ) from error

    if is_invalid_token_response(retry_response):
        raise HTTPException(
            status_code=502,
            detail=(
                "PegePay rejected the newly refreshed bearer "
                "token. Check the configured refresh token."
            ),
        )

    return retry_response


# =========================================================
# QR GUIDE IMAGE
# =========================================================

# @router.get("/qr-guide")
# def qr_guide():
#     return FileResponse(
#         "app/resources/images/qr_guide2.png",
#         media_type="image/png",
#     )


APP_DIR = (
    Path(__file__)
    .resolve()
    .parent          # pegepay
    .parent          # v2
    .parent          # controllers
    .parent          # app
)

QR_GUIDE_IMAGE = APP_DIR / "resources" / "images" / "qr_guide2.png"


@router.get("/qr-guide")
def qr_guide():
    print("APP DIR:", APP_DIR)
    print("IMAGE PATH:", QR_GUIDE_IMAGE)
    print("IMAGE EXISTS:", QR_GUIDE_IMAGE.is_file())

    if not QR_GUIDE_IMAGE.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"QR guide image not found: {QR_GUIDE_IMAGE}",
        )

    return FileResponse(
        path=str(QR_GUIDE_IMAGE),
        media_type="image/png",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
        },
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
        TTTTDDMMYYCCC

    Example:
        KN08100726001

    The order number:
        - Uses SIRIM time
        - Resets the sequence each new day
        - Has a separate sequence for each terminal
        - Supports up to 999 orders per terminal per day
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

    # Every displayed QR receives a new order number. Older
    # unprocessed rows remain untouched in MySQL and are never
    # reused for another customer or payment attempt.
    existing_order = None

    order_no = generate_pegepay_order_no(
        db=db,
        terminal_id=terminal_code,
        current_time=current_sirim_time,
    )

    print(
        "[PegePay] Creating new unique order "
        f"{order_no} for terminal "
        f"{actual_terminal_id}",
        flush=True,
    )

    payload = {
        "order_output": "online",
        "image_file_format": "png",
        "order_no": order_no,
        "override_existing_unprocessed_order_no": "no",
        "order_amount": str(body.order_amount),
        "qr_validity": str(body.qr_validity),
        "store_id": body.store_id,
        "terminal_id": actual_terminal_id,
        "shift_id": body.shift_id,
    }

    # =========================================================
    # DEBUG - OUTGOING REQUEST
    # =========================================================

    print("========================================", flush=True)
    print("[PegePay] OUTGOING REQUEST", flush=True)
    print(f"Store ID    : {payload['store_id']}", flush=True)
    print(f"Terminal ID : {payload['terminal_id']}", flush=True)
    print(f"Shift ID    : {payload['shift_id']}", flush=True)
    print(f"Order No    : {payload['order_no']}", flush=True)
    print(f"Amount      : {payload['order_amount']}", flush=True)
    print(f"QR Validity : {payload['qr_validity']}", flush=True)
    print("Payload:", flush=True)
    print(payload, flush=True)
    print("========================================", flush=True)

    # First PegePay request.
    response = pegepay_post_with_token_retry(
        db=db,
        url=PEPAY_ORDER_URL,
        payload=payload,
        timeout=30,
    )

    print("========================================", flush=True)
    print("[PegePay] RESPONSE", flush=True)
    print(f"Status Code : {response.status_code}", flush=True)
    print(f"Body        : {response.text}", flush=True)
    print("========================================", flush=True)

    # PegePay rejected the first order.
    if response.status_code != 200:
        print(
            "[PegePay] First order was rejected. "
            "Generating a new SIRIM-based order number."
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

        retry_response = pegepay_post_with_token_retry(
            db=db,
            url=PEPAY_ORDER_URL,
            payload=payload,
            timeout=30,
        )

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

    payload = {
        "order_no": body.order_no,
    }

    response = pegepay_post_with_token_retry(
        db=db,
        url=PEPAY_STATUS_URL,
        payload=payload,
        timeout=30,
    )

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
                src="https://tipintar.juaraipasifik.com/api/v2/pegepay/qr-guide"
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
