from sqlalchemy import Column, Integer, String, Float
from app.db.database import Base

class License(Base):
    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True, index=True)
    licensenum = Column(String(30), unique=True, index=True)   # e.g. LIC2025000123
    licensetype = Column(String(50), nullable=False)           # e.g. "business", "driver"
    owner_id = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String(20), nullable=False, default="unpaid")  # "unpaid" or "paid"
