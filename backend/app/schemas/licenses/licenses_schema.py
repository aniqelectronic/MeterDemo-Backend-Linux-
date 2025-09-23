from pydantic import BaseModel

class LicenseBase(BaseModel):
    licensenum: str
    owner_id: int
    amount: float
    status: str   # unpaid / paid

class LicenseCreate(LicenseBase):
    pass

class LicenseResponse(LicenseBase):
    id: int
    licensetype: str
    year: int

    class Config:
        from_attributes = True
