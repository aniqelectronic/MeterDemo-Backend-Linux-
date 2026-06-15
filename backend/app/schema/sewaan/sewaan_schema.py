
from sqlalchemy import Column, Integer, String, Float, DateTime
from app.db.database import Base


class PaymentUpdatesSewaanBentong(Base):
    __tablename__ = "payment_updates_sewaan_bentong"

    id = Column(Integer, primary_key=True, index=True)

    order_no = Column(String, index=True, nullable=False)
    
    no_pendaftaran = Column(String(100), index=True, nullable=True)
    account_number = Column(String, index=True, nullable=False)
    tenant_name = Column(String, nullable=False)
    premise_address = Column(String, nullable=False)

    amount = Column(Float, nullable=False)

    payment_method = Column(String, nullable=True)
    bank_trx_no = Column(String, nullable=True)

    paid_date = Column(DateTime, nullable=False)