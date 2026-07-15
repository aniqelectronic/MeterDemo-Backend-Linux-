# import os
# from datetime import datetime, timedelta
# from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
# from azure.storage.blob import ContentSettings
# from dotenv import load_dotenv
# from mimetypes import guess_type

# # Load .env if you have one
# load_dotenv()

# # Config
# ACCOUNT_NAME = os.getenv("ACCOUNT_NAME", "vsmeterblob")
# ACCOUNT_KEY = os.getenv("ACCOUNT_KEY", "rKu+/oWQtOQZLJ+/4RgJXKpXt3itshA38M88LX4nYE3ScM8e1BAqry708bCae0G2BQhExxyjR489+AStb/amEA==")
# CONTAINER_NAME = os.getenv("CONTAINER_NAME", "receipts")

# # Build connection string manually
# CONNECT_STR = (
#     f"DefaultEndpointsProtocol=https;"
#     f"AccountName={ACCOUNT_NAME};"
#     f"AccountKey={ACCOUNT_KEY};"
#     f"EndpointSuffix=core.windows.net"
# )


# def upload_to_blob(filename: str, content: bytes, content_type: str = None):
#     """
#     Uploads a file to Azure Blob Storage using access key
#     and returns a temporary SAS URL valid for 24 hours.
#     """
#     # Connect to Blob service
#     blob_service = BlobServiceClient.from_connection_string(CONNECT_STR)
#     container_client = blob_service.get_container_client(CONTAINER_NAME)

#     # Create container if missing
#     try:
#         container_client.create_container()
#     except Exception:
#         pass

#     # Upload blob
#     blob_client = container_client.get_blob_client(filename)
#     content_type = content_type or guess_type(filename)[0] or "application/octet-stream"
#     blob_client.upload_blob(
#         content,
#         overwrite=True,
#         content_settings=ContentSettings(content_type=content_type),
#     )

#     # Generate SAS token (valid 1 day)
#     sas_token = generate_blob_sas(
#         account_name=ACCOUNT_NAME,
#         container_name=CONTAINER_NAME,
#         blob_name=filename,
#         account_key=ACCOUNT_KEY,  # ✅ use the raw key directly
#         permission=BlobSasPermissions(read=True),
#         expiry=datetime.utcnow() + timedelta(days=1),
#     )

#     # Combine into public SAS URL
#     sas_url = f"https://{ACCOUNT_NAME}.blob.core.windows.net/{CONTAINER_NAME}/{filename}?{sas_token}"
#     return sas_url


import os
from datetime import datetime, timedelta, timezone
from mimetypes import guess_type
from urllib.parse import quote

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import (
    BlobServiceClient,
    BlobSasPermissions,
    ContentSettings,
    generate_blob_sas,
)
from dotenv import load_dotenv


# Load .env
load_dotenv()


# ============================================================
# CONFIG
# ============================================================

ACCOUNT_NAME = os.getenv("ACCOUNT_NAME", "vsmeterblob")
ACCOUNT_KEY = os.getenv("ACCOUNT_KEY", "rKu+/oWQtOQZLJ+/4RgJXKpXt3itshA38M88LX4nYE3ScM8e1BAqry708bCae0G2BQhExxyjR489+AStb/amEA==")
CONTAINER_NAME = os.getenv("CONTAINER_NAME", "receipts")

# This is your new public receipt domain
PUBLIC_BLOB_DOMAIN = os.getenv(
    "PUBLIC_BLOB_DOMAIN",
    "https://tipintar.juaraipasifik.com",
).rstrip("/")


if not ACCOUNT_KEY:
    raise RuntimeError(
        "ACCOUNT_KEY is missing. Add it inside your .env file."
    )


# ============================================================
# AZURE CONNECTION STRING
# ============================================================

CONNECT_STR = (
    "DefaultEndpointsProtocol=https;"
    f"AccountName={ACCOUNT_NAME};"
    f"AccountKey={ACCOUNT_KEY};"
    "EndpointSuffix=core.windows.net"
)


blob_service = BlobServiceClient.from_connection_string(CONNECT_STR)


# ============================================================
# UPLOAD FUNCTION
# ============================================================

def upload_to_blob(
    filename: str,
    content: bytes,
    content_type: str | None = None,
) -> str:
    """
    Upload a file to Azure Blob Storage and return a temporary
    read-only SAS URL using tipintar.juaraipasifik.com.
    """

    if not filename:
        raise ValueError("filename cannot be empty")

    if not isinstance(content, bytes):
        raise TypeError("content must be bytes")

    container_client = blob_service.get_container_client(CONTAINER_NAME)

    # Create container if it does not already exist
    try:
        container_client.create_container()
    except ResourceExistsError:
        pass

    resolved_content_type = (
        content_type
        or guess_type(filename)[0]
        or "application/octet-stream"
    )

    blob_client = container_client.get_blob_client(filename)

    # Upload the file
    blob_client.upload_blob(
        content,
        overwrite=True,
        content_settings=ContentSettings(
            content_type=resolved_content_type,
        ),
    )

    # Create read-only SAS token
    sas_token = generate_blob_sas(
        account_name=ACCOUNT_NAME,
        container_name=CONTAINER_NAME,
        blob_name=filename,
        account_key=ACCOUNT_KEY,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    # Encode spaces and special characters in filename
    encoded_filename = quote(filename, safe="/")

    # Return custom-domain URL instead of blob.core.windows.net
    sas_url = (
        f"{PUBLIC_BLOB_DOMAIN}/"
        f"{CONTAINER_NAME}/"
        f"{encoded_filename}"
        f"?{sas_token}"
    )

    return sas_url