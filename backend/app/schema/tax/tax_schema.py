from sqlalchemy import Column, Integer, String, Float
from app.db.database import Base

class Tax(Base):
    __tablename__ = "taxes"

    id = Column(Integer, primary_key=True, index=True)
    taxnum = Column(String(30), unique=True, index=True)   # e.g. TAX2025000123
    taxtype = Column(String(50), nullable=False)           # e.g. "property", "income"
    owner_id = Column(Integer, nullable=False)
    property_id = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String(20), nullable=False, default="unpaid")  # "unpaid" or "paid"
