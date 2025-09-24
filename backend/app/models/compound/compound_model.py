from pydantic import BaseModel
from datetime import date, time
from enum import Enum


class StatusTypeEnum(str, Enum):
    paid = "PAID"
    unpaid = "UNPAID"
    
class CompoundBase(BaseModel):
    compoundnum: str
    plate: str
    date: date
    time: time
    offense: str
    amount: float
    status: StatusTypeEnum

class CompoundCreate(CompoundBase):
    pass

class CompoundResponse(CompoundBase):
    id: int

    class Config:
        orm_mode = True
