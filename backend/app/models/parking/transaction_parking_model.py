# app/schemas/transaction_parking_schema.py
from pydantic import BaseModel
from enum import Enum
from datetime import datetime

class TransactionTypeEnum(str, Enum):
    new = "new"
    extend = "extend"

class TransactionResponse(BaseModel):
    id: int
    ticket_id: str
    plate: str
    hours: float
    amount: float
    receipt_url: str
    transaction_type: TransactionTypeEnum
    
    
    class Config:
        from_attributes = True 
        
        
class TransactionCreate(BaseModel):
    ticket_id: str
    plate: str
    hours: float
    amount: float
    transaction_type: TransactionTypeEnum

    class Config:
        from_attributes = True 
