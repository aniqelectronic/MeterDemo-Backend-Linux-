import base64
import hashlib
import hmac
import os
from urllib.parse import parse_qsl, quote

from fastapi import HTTPException, Request, status


TIP_API_KEY = os.getenv("TIP_API_KEY", "")
TIP_HMAC_SECRET = os.getenv("TIP_HMAC_SECRET", "")


if not TIP_API_KEY:
    raise RuntimeError(
        "TIP_API_KEY environment variable is missing."
    )

if not TIP_HMAC_SECRET:
    raise RuntimeError(
        "TIP_HMAC_SECRET environment variable is missing."
    )


def _body_sha256_base64(body: bytes) -> str:
    digest = hashlib.sha256(body).digest()
    return base64.b64encode(digest).decode("ascii")


def _canonical_query(request: Request) -> str:
    query_items = parse_qsl(
        request.url.query,
        keep_blank_values=True,
    )

    query_items.sort(
        key=lambda item: (item[0], item[1])
    )

    encoded_items = []

    for key, value in query_items:
        encoded_key = quote(key, safe="-._~")
        encoded_value = quote(value, safe="-._~")

        encoded_items.append(
            f"{encoded_key}={encoded_value}"
        )

    return "&".join(encoded_items)


def _build_canonical_string(
    *,
    method: str,
    path: str,
    query: str,
    body_hash: str,
) -> str:
    return "\n".join(
        [
            method.upper(),
            path,
            query,
            body_hash,
        ]
    )


def _generate_expected_signature(
    canonical_string: str,
) -> str:
    signature = hmac.new(
        TIP_HMAC_SECRET.encode("utf-8"),
        canonical_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return f"v1={signature}"


async def require_api_key_and_hmac(
    request: Request,
) -> None:
    request_path = request.url.path.rstrip("/")

    # Allow only the QR guide image without API key/HMAC.
    if (
        request.method.upper() == "GET"
        and request_path
        == "/api/v2/pegepay/qr-guide"
    ):
        return

    received_api_key = request.headers.get(
        "X-API-Key"
    )

    received_signature = request.headers.get(
        "X-Signature"
    )

    if not received_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header.",
        )

    if not received_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Signature header.",
        )

    if not hmac.compare_digest(
        received_api_key,
        TIP_API_KEY,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )

    request_body = await request.body()

    body_hash = _body_sha256_base64(
        request_body
    )

    canonical_string = _build_canonical_string(
        method=request.method,
        path=request.url.path,
        query=_canonical_query(request),
        body_hash=body_hash,
    )

    expected_signature = (
        _generate_expected_signature(
            canonical_string
        )
    )

    if not hmac.compare_digest(
        received_signature,
        expected_signature,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid HMAC signature.",
        )