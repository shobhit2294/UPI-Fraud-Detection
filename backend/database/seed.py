"""
Seeds a small mock payee directory so /payees/verify has something to check
against. This simulates the "account holder name lookup + dummy account
flag" that real UPI apps get from NPCI's mapper service -- we obviously
don't have access to that, so this is a stand-in demo dataset.

Run with:  python -m database.seed   (from backend/)
It's also called automatically once at API startup if the payees table is empty.
"""

from database.db import SessionLocal
from models.transaction import Payee

DEMO_PAYEES = [
    {"vpa": "college.fees@icici", "account_holder_name": "ABC College of Engineering", "bank": "ICICI Bank", "is_verified": True, "is_dummy": False},
    {"vpa": "rahul.sharma@okhdfc", "account_holder_name": "Rahul Sharma", "bank": "HDFC Bank", "is_verified": True, "is_dummy": False},
    {"vpa": "priya.verma@oksbi", "account_holder_name": "Priya Verma", "bank": "State Bank of India", "is_verified": True, "is_dummy": False},
    {"vpa": "electric.board@paytm", "account_holder_name": "State Electricity Board", "bank": "Paytm Payments Bank", "is_verified": True, "is_dummy": False},
    {"vpa": "quickrich.offer@fakepay", "account_holder_name": "Unknown / Unregistered", "bank": "Unknown", "is_verified": False, "is_dummy": True},
    {"vpa": "support.refund@scampay", "account_holder_name": "Unknown / Unregistered", "bank": "Unknown", "is_verified": False, "is_dummy": True},
]


def seed_payees():
    db = SessionLocal()
    try:
        if db.query(Payee).count() > 0:
            return
        for p in DEMO_PAYEES:
            db.add(Payee(**p))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed_payees()
    print("Seeded demo payees.")
