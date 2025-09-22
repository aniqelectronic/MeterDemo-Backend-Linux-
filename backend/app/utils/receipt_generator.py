# app/utils/receipt_generator.py

BASE_RECEIPT_URL = "http://localhost:8000/transactions/receipt"

def generate_receipt_url(ticket_id: str) -> str:
    """
    Build receipt URL for a given ticket_id.
    Example: http://localhost:8000/transactions/receipt/P-0001
    """
    return f"{BASE_RECEIPT_URL}/{ticket_id}"
