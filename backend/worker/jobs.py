"""
The actual settlement simulation. This is what the reconciliation-worker
process runs (via `rq worker`) for each queued transaction.

It simulates the real multi-hop chain you described:
  your bank (NetBanking) -> PSP (PayU/HDFC) -> aggregator (EasyPay/ICICI) -> merchant bank
writing one TransactionEvent per hop so the frontend can show a live timeline,
and lands on SETTLED / FAILED / STUCK_PENDING_RECONCILIATION -- the last one
being exactly the "bank says success, merchant says nothing received" case.
"""

import random
import time

from database.db import SessionLocal
from models.transaction import Transaction, TransactionEvent, TransactionStatus
from config import (
    SETTLEMENT_MIN_DELAY_SECONDS,
    SETTLEMENT_MAX_DELAY_SECONDS,
    SETTLEMENT_STUCK_PROBABILITY,
    SETTLEMENT_FAIL_PROBABILITY,
)

HOPS = [
    ("BANK_ACK", "Sender's Bank (NetBanking)"),
    ("PSP_PROCESSING", "Payment Service Provider (e.g. PayU / HDFC)"),
    ("AGGREGATOR_PROCESSING", "Aggregator (e.g. EasyPay / ICICI)"),
]


def _log_event(db, transaction_id, stage, status, actor, message=None):
    db.add(TransactionEvent(
        transaction_id=transaction_id,
        stage=stage,
        status=status,
        actor=actor,
        message=message,
    ))
    db.commit()


def run_settlement(transaction_id: int):
    db = SessionLocal()
    try:
        tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not tx:
            return

        for stage, actor in HOPS:
            time.sleep(random.uniform(SETTLEMENT_MIN_DELAY_SECONDS, SETTLEMENT_MAX_DELAY_SECONDS))
            tx.status = stage
            db.commit()
            _log_event(db, transaction_id, stage, "OK", actor)

        roll = random.random()

        if roll < SETTLEMENT_FAIL_PROBABILITY:
            tx.status = TransactionStatus.FAILED.value
            db.commit()
            _log_event(
                db, transaction_id, "FAILED", "FAILED",
                "Merchant / Payee Bank",
                "Settlement explicitly failed and the amount will be auto-reversed."
            )
        elif roll < SETTLEMENT_FAIL_PROBABILITY + SETTLEMENT_STUCK_PROBABILITY:
            tx.status = TransactionStatus.STUCK_PENDING_RECONCILIATION.value
            db.commit()
            _log_event(
                db, transaction_id, "STUCK_PENDING_RECONCILIATION", "DELAYED",
                "Merchant / Payee Bank",
                "Debited from sender but not yet confirmed at the merchant/payee bank -- "
                "pending manual reconciliation. This mirrors the real 'my bank shows success, "
                "the receiver shows nothing' scenario; in production this needs a bank/NPCI dispute."
            )
        else:
            tx.status = TransactionStatus.SETTLED.value
            db.commit()
            _log_event(
                db, transaction_id, "SETTLED", "OK",
                "Merchant / Payee Bank",
                "Amount confirmed received at the merchant/payee account."
            )
    finally:
        db.close()
