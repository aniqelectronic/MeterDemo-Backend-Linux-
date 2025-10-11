from sqlalchemy import Column, String, Integer, Float, Date, Enum
from app.db.database import Base
from app.models.licenses.licenses_model import StatusTypeEnum

class License(Base):
    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True, index=True)
    licensenum = Column(String(30), unique=True, index=True)  # add length
    licensetype = Column(String(50))                                # add length
    owner_id = Column(String(50))                                   # add length
    year = Column(Integer)
    amount = Column(Float)
    status = Column(Enum(StatusTypeEnum), default=StatusTypeEnum.unpaid, nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
