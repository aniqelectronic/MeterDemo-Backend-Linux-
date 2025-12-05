from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from datetime import datetime
from app.db.database import Base
from sqlalchemy.orm import relationship

# -----------------------------
# Owners table
# -----------------------------
class Owner(Base):
    __tablename__ = "owners"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    ic = Column(String(20))
    phone = Column(String(30))
    email = Column(String(120))
    address = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationship
    properties = relationship("Property", back_populates="owner")
    taxes = relationship("CukaiTaksiran", back_populates="owner")


# -----------------------------
# Properties table
# -----------------------------
class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=False)
    
    account_no = Column(String(50), unique=True, nullable=False)
    lot_no = Column(String(50))
    house_no = Column(String(50))
    street = Column(String(120))
    address1 = Column(String(150))
    address2 = Column(String(150))
    zone = Column(String(50))
    property_type = Column(String(50))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationship
    owner = relationship("Owner", back_populates="properties")
    taxes = relationship("CukaiTaksiran", back_populates="property")


class CukaiTaksiran(Base):
    __tablename__ = "cukai_taksiran"

    id = Column(Integer, primary_key=True, index=True)
    
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=False)

    # Cached copy of owner name
    owner_name = Column(String(150))

    # Valuation fields
    annual_value = Column(Float, nullable=False)
    rate_percent = Column(Float, nullable=False)
    half_year_amount = Column(Float, nullable=False)

    # Billing cycle
    year = Column(Integer, nullable=False)
    cycle = Column(String(10), nullable=False)  # H1 / H2
    bill_no = Column(String(50), unique=True)
    issue_date = Column(DateTime)
    due_date = Column(DateTime)

    # Audit
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships
    property = relationship("Property", back_populates="taxes")
    owner = relationship("Owner", back_populates="taxes")