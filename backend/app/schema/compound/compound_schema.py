from sqlalchemy import Column, Integer, String, Float, Date, Time , Enum
from app.db.database import Base
import enum

# Enum for transaction type
class StatusTypeEnum(str, enum.Enum):
    unpaid = "UNPAID"
    paid = "PAID"
    
class Compound(Base):
    __tablename__ = "compounds"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)
    compoundnum = Column(String(30), unique=True, index=True)  
    plate = Column(String(50), index=True)
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    offense = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(Enum(StatusTypeEnum), nullable=False)

class MultiCompound(Base):
    __tablename__ = "multi_compound"

    id = Column(Integer, primary_key=True, index=True)
    transaction_bank_id = Column(String(100), index=True)
    compoundnum = Column(String(30), index=True)