from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.db import SessionLocal
from utils.jwt import verify_token
from models.transaction import Transaction
from ml.fraud_model import predict_fraud

router = APIRouter(prefix="/transactions", tags=["Transactions"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/")
def create_transaction(amount: float, user=Depends(verify_token), db: Session = Depends(get_db)):
    status, risk = predict_fraud(amount)

    tx = Transaction(amount=amount, status=status, risk=risk)
    db.add(tx)
    db.commit()
    db.refresh(tx)

    return tx

@router.get("/")
def get_transactions(user=Depends(verify_token), db: Session = Depends(get_db)):
    return db.query(Transaction).order_by(Transaction.id.desc()).all()
