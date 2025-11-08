from pydantic import BaseModel

class MultiCompoundBase(BaseModel):
    transaction_bank_id: str
    compoundnum: str

class MultiCompoundCreate(MultiCompoundBase):
    pass

class MultiCompoundResponse(MultiCompoundBase):
    id: int

    class Config:
        orm_mode = True
