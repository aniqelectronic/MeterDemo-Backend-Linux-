from sqlalchemy import Column, Integer, String, Float, Date, Time
from app.db.database import Base

class Compound(Base):
    __tablename__ = "compounds"

    id = Column(Integer, primary_key=True, index=True)
    compoundnum = Column(String(30), unique=True, index=True)  
    plate = Column(String(50), index=True)
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    offense = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
