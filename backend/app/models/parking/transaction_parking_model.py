# app/schemas/transaction_parking_schema.py
from pydantic import BaseModel
from enum import Enum
from datetime import datetime

class TicketOverviewEnum(str, Enum):
    new = "new"
    extend = "extend"
    

class TransactionResponse(BaseModel):
    id: int
    terminal: str 
    ticket_id: str
    plate: str
    hours: float
    amount: float
    transaction_type: str
    Ticket_Overview: TicketOverviewEnum
    order_no: str | None = None
    bank_trx_no: str | None = None
    
    
    class Config:
        from_attributes = True 
        
        
class TransactionCreate(BaseModel):
    ticket_id: str
    terminal: str 
    plate: str
    hours: float
    amount: float
    transaction_type: str
    Ticket_Overview: TicketOverviewEnum
    order_no: str | None = None
    bank_trx_no: str | None = None

    class Config:
        from_attributes = True 
