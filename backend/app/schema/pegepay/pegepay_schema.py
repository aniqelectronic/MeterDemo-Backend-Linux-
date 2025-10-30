from sqlalchemy import Column, Integer, String, Float,BigInteger
from app.db.database import Base

class PegepayOrder(Base):
    __tablename__ = "pegepay_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(50), unique=True, index=True)
    order_amount = Column(Float)
    order_status = Column(String(50))
    store_id = Column(String(100))
    terminal_id = Column(String(100))
    
class PegepayToken(Base):
    __tablename__ = "pegepay_token"

    id = Column(Integer, primary_key=True, index=True)
    access_token = Column(String(512), nullable=False)
    token_expired_at = Column(BigInteger, nullable=False)
