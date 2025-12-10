from sqlalchemy import Column, String, Integer, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


class OwnerLicense(Base):
    __tablename__ = "ownerlicense"  # Renamed table

    ic = Column(String(20), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), nullable=True)
    address = Column(String(255), nullable=True)

    # One owner can have MANY licenses
    licenses = relationship("License", back_populates="owner")


class License(Base):
    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True, index=True)
    licensenum = Column(String(30), unique=True, index=True, nullable=False)
    licensetype = Column(String(50), nullable=False)

    # Link by IC to ownerlicense table
    ic = Column(String(20), ForeignKey("ownerlicense.ic"), nullable=False)

    amount = Column(Float, nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    # Relationship – each license belongs to one owner
    owner = relationship("OwnerLicense", back_populates="licenses")
