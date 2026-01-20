from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime
from datetime import datetime
from database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)

    transaction_id = Column(Integer, unique=True, index=True)
    amount = Column(Float)

    device_type = Column(String)
    location = Column(String)

    fraud = Column(Boolean)
    risk_score = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)
