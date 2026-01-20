from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database.db import SessionLocal
from models.transaction import Transaction
from utils.jwt import verify_token

router = APIRouter(prefix="/analytics", tags=["Analytics"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/daily")
def daily_analytics(user=Depends(verify_token), db: Session = Depends(get_db)):
    result = (
        db.query(func.date(Transaction.created_at), func.count(Transaction.id))
        .group_by(func.date(Transaction.created_at))
        .all()
    )

    return {
        "labels": [str(r[0]) for r in result],
        "counts": [r[1] for r in result]
    }
