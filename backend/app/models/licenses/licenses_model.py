from pydantic import BaseModel
from enum import Enum
from datetime import date

class LicenseBase(BaseModel):
    licensenum: str
    owner_id: int
    amount: float
    status: str   # unpaid / paid

class LicenseCreate(LicenseBase):
    pass

class LicenseResponse(LicenseBase):
    licensenum: str
    licensetype: str
    owner_id: int
    year: int
    amount: float
    status: str
    id: int
    start_date: date | None = None
    end_date: date | None = None

    class Config:
        from_attributes = True

class StatusTypeEnum(str, Enum):
    unpaid = "unpaid"
    active = "active"
    expired = "expired"