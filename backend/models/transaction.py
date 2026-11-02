from sqlalchemy import (
    Column, Integer, Float, Boolean, String, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from database.db import Base
from datetime import datetime
import enum


class TransactionStatus(str, enum.Enum):
    INITIATED = "INITIATED"                          # created, queued for settlement
    OTP_REQUIRED = "OTP_REQUIRED"                     # high risk, waiting on step-up OTP
    BANK_ACK = "BANK_ACK"                             # your bank acknowledged debit
    PSP_PROCESSING = "PSP_PROCESSING"                 # PSP (e.g. PayU) processing
    AGGREGATOR_PROCESSING = "AGGREGATOR_PROCESSING"   # aggregator (e.g. EasyPay) processing
    SETTLED = "SETTLED"                               # money confirmed at merchant/payee bank
    FAILED = "FAILED"                                 # explicitly failed / reversed
    STUCK_PENDING_RECONCILIATION = "STUCK_PENDING_RECONCILIATION"  # your real-world scenario


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)

    amount = Column(Float)
    risk = Column(Float)
    is_fraud = Column(Boolean, default=False)

    user_id = Column(String, index=True)

    # ---- payee verification ----
    payee_vpa = Column(String, nullable=True)
    payee_name = Column(String, nullable=True)
    payee_verified = Column(Boolean, default=False)
    payee_is_dummy = Column(Boolean, default=False)

    # ---- geolocation fraud signal ----
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location_is_new_for_user = Column(Boolean, default=False)

    # ---- OTP step-up ----
    otp_required = Column(Boolean, default=False)
    otp_verified = Column(Boolean, default=False)

    # ---- multi-hop settlement status ----
    status = Column(String, default=TransactionStatus.INITIATED.value, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    events = relationship(
        "TransactionEvent",
        back_populates="transaction",
        order_by="TransactionEvent.created_at",
        cascade="all, delete-orphan",
    )


class TransactionEvent(Base):
    """
    One row per hop in the settlement chain, e.g.:
    your bank -> PSP (PayU/HDFC) -> aggregator (EasyPay/ICICI) -> merchant bank.
    This is what powers the live timeline the user asked to be able to track.
    """
    __tablename__ = "transaction_events"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), index=True)

    stage = Column(String)     # e.g. "BANK_ACK", "PSP_PROCESSING", ...
    status = Column(String)    # "OK" / "DELAYED" / "FAILED"
    actor = Column(String)     # e.g. "Indian Bank (NetBanking)", "PayU (HDFC)", "EasyPay (ICICI)"
    message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    transaction = relationship("Transaction", back_populates="events")


class Payee(Base):
    """
    Mock payee directory used to simulate 'is this a dummy/verified account'
    and 'what name is registered' checks that real UPI apps do before payment.
    Seeded with demo data -- see database/seed.py.
    """
    __tablename__ = "payees"

    id = Column(Integer, primary_key=True, index=True)
    vpa = Column(String, unique=True, index=True)
    account_holder_name = Column(String)
    bank = Column(String)
    is_verified = Column(Boolean, default=True)
    is_dummy = Column(Boolean, default=False)


class OtpChallenge(Base):
    """
    Step-up OTP issued when a transaction crosses the risk threshold.
    In this demo there's no SMS gateway, so the code is only ever exposed
    back to the caller when config.DEMO_MODE is true -- clearly labeled as
    a demo OTP, never something you'd do with a real one-time password.
    """
    __tablename__ = "otp_challenges"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), index=True)

    code_hash = Column(String)
    attempts = Column(Integer, default=0)
    verified = Column(Boolean, default=False)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
