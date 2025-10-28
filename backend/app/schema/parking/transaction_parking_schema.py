from sqlalchemy import Column, Integer, String, Float, DateTime, Enum
from app.db.database import Base
import enum



# Enum for Ticket Overview
class TicketOverviewEnum(str, enum.Enum):
    new = "new"
    extend = "extend"

class TransactionParking(Base):   
    __tablename__ = "transaction_parkings"   

    id = Column(Integer, primary_key=True, index=True)
    terminal = Column(String(50), nullable=False)
    ticket_id = Column(String(20), unique=True, index=True)  # e.g., P-0001
    plate = Column(String(50), index=True)
    hours = Column(Float, nullable=False)  # total hours paid
    amount = Column(Float, nullable=False)
    Transaction_type = Column(String(50), nullable=False)
    receipt_url = Column(String(255), default="https://dummyurl.com/receipt/")
    Ticket_Overview = Column(Enum(TicketOverviewEnum), nullable=False) 
