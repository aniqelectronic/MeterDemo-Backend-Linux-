import os
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from dotenv import load_dotenv
from mimetypes import guess_type

# Load .env
load_dotenv()

# Read from .env
AZURE_STORAGE_CONNECTION = os.getenv("DefaultEndpointsProtocol")
ACCOUNT_NAME = "vsmeterblob"
CONTAINER_NAME = "receipts"


def upload_to_blob(filename: str, content: bytes, content_type: str = None):
    """
    Uploads a file (PDF, HTML, etc.) to Azure Blob Storage using access key.
    Returns a SAS URL valid for 1 day (temporary public access).
    """
    # Create blob service
    blob_service = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION)

    # Ensure container exists
    container_client = blob_service.get_container_client(CONTAINER_NAME)
    try:
        container_client.create_container()
    except Exception:
        pass  # already exists

    # Upload
    blob_client = container_client.get_blob_client(filename)
    content_type = content_type or guess_type(filename)[0] or "application/octet-stream"
    blob_client.upload_blob(content, overwrite=True, content_settings={"content_type": content_type})

    # Generate temporary SAS URL (24h)
    sas_token = generate_blob_sas(
        account_name=ACCOUNT_NAME,
        container_name=CONTAINER_NAME,
        blob_name=filename,
        account_key=blob_service.credential.account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(days=1)
    )

    return f"{blob_client.url}?{sas_token}"
