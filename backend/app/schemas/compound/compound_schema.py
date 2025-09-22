from pydantic import BaseModel
from datetime import date, time

class CompoundBase(BaseModel):
    compoundnum: str
    plate: str
    date: date
    time: time
    offense: str
    amount: float

class CompoundCreate(CompoundBase):
    pass

class CompoundResponse(CompoundBase):
    id: int

    class Config:
        orm_mode = True
