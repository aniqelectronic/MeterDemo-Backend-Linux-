from pydantic import BaseModel
from datetime import datetime
from enum import Enum

# -------------------------
# Request Schemas
# -------------------------
class ParkingCheck(BaseModel):
    plate: str

class ParkingCreate(BaseModel):
    plate: str
    time_used: float  

class ParkingExtend(BaseModel):
    extend_hours: float

# -------------------------
# Response Schema
# -------------------------
class PaymentStatusEnum(str, Enum):
    yes = "yes"
    no = "no"

class ParkingResponse(BaseModel):
    id: int
    plate: str
    time_used: float
    payment_status: PaymentStatusEnum
    timein: datetime
    timeout: datetime
    amount: float

    class Config:
        orm_mode = True
