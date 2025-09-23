from pydantic import BaseModel

class TaxBase(BaseModel):
    taxnum: str
    taxtype: str
    owner_id: int
    property_id: int
    year: int
    amount: float
    status: str   # "unpaid" / "paid"


#Just reusing all fields from TaxBase
class TaxCreate(TaxBase):
    pass

class TaxResponse(TaxBase):
    id: int

    class Config:
        from_attributes = True   # ✅ for Pydantic v2
