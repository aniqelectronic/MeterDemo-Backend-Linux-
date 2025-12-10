from pydantic import BaseModel
from datetime import date

class LicenseBase(BaseModel):
    licensenum: str
    ic: str             # links to OwnerLicense
    amount: float

class LicenseCreate(LicenseBase):
    licensetype: str | None = None  # optional, can be auto-set

class LicenseResponse(LicenseBase):
    id: int
    licensetype: str
    start_date: date | None = None
    end_date: date | None = None

    class Config:
        from_attributes = True


class OwnerLicenseBase(BaseModel):
    ic: str
    name: str
    email: str | None = None
    address: str | None = None

class OwnerLicenseCreate(OwnerLicenseBase):
    pass

class OwnerLicenseResponse(OwnerLicenseBase):
    class Config:
        from_attributes = True
