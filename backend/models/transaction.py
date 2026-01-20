from sqlalchemy import Column, Integer, Float, String, DateTime
from datetime import datetime
from database.db import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float)
    status = Column(String)
    risk = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
