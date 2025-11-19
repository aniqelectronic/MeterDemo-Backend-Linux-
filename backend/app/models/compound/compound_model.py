from pydantic import BaseModel
from datetime import date, time
from enum import Enum
from typing import Optional

class StatusTypeEnum(str, Enum):
    paid = "PAID"
    unpaid = "UNPAID"
    
class CompoundBase(BaseModel):
    name: str
    compoundnum: str
    plate: str
    date: date
    time: time
    offense: str
    amount: float
    status: Optional[StatusTypeEnum] = None

class CompoundCreate(CompoundBase):
    pass

class CompoundResponse(CompoundBase):
    id: int

    class Config:
        orm_mode = True