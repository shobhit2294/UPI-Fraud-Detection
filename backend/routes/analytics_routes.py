from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, Integer, cast

from database.db import get_db
from models.transaction import Transaction
from middleware.auth import owner_only

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary")
def analytics_summary(
    user=Depends(owner_only),
    db: Session = Depends(get_db),
):
    total = db.query(Transaction).count()
    fraud = db.query(Transaction).filter(Transaction.is_fraud == True).count()

    return {
        "total_transactions": total,
        "fraud_transactions": fraud,
        "safe_transactions": total - fraud,
        "fraud_percentage": round((fraud / total) * 100, 2) if total else 0,
    }


@router.get("/daily")
def daily_analytics(
    user=Depends(owner_only),
    db: Session = Depends(get_db),
):
    data = (
        db.query(
            func.date(Transaction.created_at),
            func.count(Transaction.id),
            func.sum(cast(Transaction.is_fraud, Integer)),
        )
        .group_by(func.date(Transaction.created_at))
        .all()
    )

    result = []
    for d in data:
        result.append({
            "date": str(d[0]),
            "total": d[1],
            "fraud": int(d[2] or 0),
        })
    return result
