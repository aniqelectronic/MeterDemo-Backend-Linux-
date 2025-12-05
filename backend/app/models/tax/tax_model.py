from typing import List
from pydantic import BaseModel
from datetime import datetime

# -----------------------------
# Base schema
# -----------------------------
class TaxBase(BaseModel):
    property_id: int
    owner_id: int
    owner_name: str | None = None
    annual_value: float
    rate_percent: float
    half_year_amount: float
    year: int
    cycle: str  # H1 / H2
    bill_no: str | None = None
    issue_date: datetime | None = None
    due_date: datetime | None = None
    status: str = "unpaid"  # unpaid / paid
    paid_amount: float | None = 0.0
    paid_date: datetime | None = None
    payment_ref: str | None = None
    penalty_amount: float | None = 0.0
    arrears: float | None = 0.0
    total_payable: float | None = 0.0


# -----------------------------
# Create schema
# -----------------------------
class TaxCreate(TaxBase):
    pass

class OwnerCreate(BaseModel):
    name: str
    ic: str
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    

class PropertyCreate(BaseModel):
    owner_id: int
    account_no: str
    lot_no: str | None = None
    house_no: str | None = None
    street: str | None = None
    address1: str | None = None
    address2: str | None = None
    zone: str | None = None
    property_type: str | None = None

class TaxPaymentItem(BaseModel):
    bill_no: str
    paid_amount: float
    payment_ref: str | None = None

class TaxPaymentRequest(BaseModel):
    payments: List[TaxPaymentItem]
    paid_date: datetime | None = None  # optional, default to now
    
    
# -----------------------------
# Response schema
# -----------------------------
class TaxResponse(TaxBase):
    id: int

    class Config:
        from_attributes = True  # ✅ Pydantic v2
