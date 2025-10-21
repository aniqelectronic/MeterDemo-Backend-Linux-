from sqlalchemy import Column, Integer, String, Enum, DateTime, Float , DECIMAL
from app.db.database import Base
import enum
from datetime import timedelta
from app.utils.Malaysia_time import malaysia_now




# -------------------------
# Enum for payment status
# -------------------------
class PaymentStatusEnum(str, enum.Enum):
    yes = "yes"
    no = "no"


# -------------------------
# SQLAlchemy Parking model
# -------------------------
class Parking(Base):
    __tablename__ = "parkings"

    id = Column(Integer, primary_key=True, index=True)
    terminal = Column(Integer, nullable=False)
    plate = Column(String(50), index=True)
    time_used = Column(Float)
    payment_status = Column(Enum(PaymentStatusEnum), default=PaymentStatusEnum.no)
    timein = Column(DateTime, default=malaysia_now, nullable=False)   # ✅ default Malaysia time
    timeout = Column(DateTime, nullable=True)
    amount = Column(Float, default=0.0)
    

    def set_timeout(self):
        """Calculate timeout = timein + time_used (hours)"""
        if self.timein and self.time_used is not None:
            self.timeout = self.timein + timedelta(hours=self.time_used)

