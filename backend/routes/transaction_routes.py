import math

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.db import get_db
from middleware.auth import get_current_user, owner_only
from models.transaction import Transaction, TransactionEvent, TransactionStatus, Payee, OtpChallenge
from schemas.transaction_schema import (
    TransactionRequest, TransactionResponse, OtpVerifyRequest, TransactionEventOut,
)
from ml.predictor import predict_fraud
from utils.otp import generate_otp, verify_otp
from worker.queue import settlement_queue
from worker.jobs import run_settlement
from config import OTP_REQUIRED_RISK_THRESHOLD, DEMO_MODE

router = APIRouter(prefix="/transactions", tags=["Transactions"])

# Roughly how far (in km) counts as "a new location" for the user, for the
# geolocation fraud signal. This is a simple demo heuristic, not a real
# device-fingerprinting/geo-fencing system.
NEW_LOCATION_THRESHOLD_KM = 100


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


def _is_new_location(db: Session, user_id: str, lat: float, lon: float) -> bool:
    last = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.latitude.isnot(None),
            Transaction.longitude.isnot(None),
        )
        .order_by(Transaction.created_at.desc())
        .first()
    )
    if not last:
        return False  # first transaction ever -- nothing to compare against
    return _haversine_km(last.latitude, last.longitude, lat, lon) > NEW_LOCATION_THRESHOLD_KM


# ---------------- CREATE TRANSACTION ----------------

@router.post("/", response_model=TransactionResponse)
def create_transaction(
    data: TransactionRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = user.get("uid") or str(user.get("id"))

    # ---- 1. Payee verification (name + dummy-account check) ----
    payee = db.query(Payee).filter(Payee.vpa == data.payee_vpa.strip().lower()).first()
    payee_verified = bool(payee and payee.is_verified and not payee.is_dummy)
    payee_is_dummy = bool(payee and payee.is_dummy) or payee is None
    payee_name = payee.account_holder_name if payee else None

    if payee and payee.is_dummy:
        raise HTTPException(
            status_code=400,
            detail=f"Payment blocked: '{data.payee_vpa}' is flagged as a known dummy/suspicious account.",
        )

    # ---- 2. Geolocation signal ----
    location_is_new = False
    if data.latitude is not None and data.longitude is not None:
        location_is_new = _is_new_location(db, user_id, data.latitude, data.longitude)

    # ---- 3. ML fraud/risk scoring (fraud-ml-service) ----
    payload = {
        "Transaction_Amount": data.amount,
        "Account_Balance": data.balance,
        "City": data.city,
        "Device_Type": data.device,
        "Transaction_Type": data.transaction_type,
        "Age": user.get("age", 28),
        "user_id": user_id,
    }
    is_fraud, risk, _risk_details = predict_fraud(payload)

    # Unverified payee or a new/unusual location nudges the risk score up --
    # this is the "location mismatch" / "unknown recipient" signal you asked about.
    if not payee_verified:
        risk = min(100, risk + 15)
    if location_is_new:
        risk = min(100, risk + 10)
    is_fraud = risk >= 60

    otp_required = risk >= OTP_REQUIRED_RISK_THRESHOLD

    tx = Transaction(
        amount=data.amount,
        is_fraud=is_fraud,
        risk=risk,
        user_id=user_id,
        payee_vpa=data.payee_vpa,
        payee_name=payee_name,
        payee_verified=payee_verified,
        payee_is_dummy=payee_is_dummy,
        latitude=data.latitude,
        longitude=data.longitude,
        location_is_new_for_user=location_is_new,
        otp_required=otp_required,
        status=(
            TransactionStatus.OTP_REQUIRED.value
            if otp_required else TransactionStatus.INITIATED.value
        ),
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    demo_otp_code = None

    if otp_required:
        code, code_hash, expires_at = generate_otp()
        db.add(OtpChallenge(transaction_id=tx.id, code_hash=code_hash, expires_at=expires_at))
        db.commit()
        db.add(TransactionEvent(
            transaction_id=tx.id, stage="OTP_REQUIRED", status="PENDING",
            actor="Fraud Engine",
            message=f"Risk score {risk}% crossed the step-up threshold -- OTP required before settlement.",
        ))
        db.commit()
        if DEMO_MODE:
            demo_otp_code = code  # DEMO ONLY: a real OTP would never be returned in an API response
    else:
        db.add(TransactionEvent(
            transaction_id=tx.id, stage="INITIATED", status="OK",
            actor="Payment Orchestrator", message="Transaction accepted, queued for settlement.",
        ))
        db.commit()
        settlement_queue.enqueue(run_settlement, tx.id)

    return TransactionResponse(
        id=tx.id, amount=tx.amount, is_fraud=tx.is_fraud, risk=tx.risk,
        status=tx.status, otp_required=tx.otp_required,
        payee_name=tx.payee_name, payee_verified=tx.payee_verified,
        demo_otp_code=demo_otp_code,
    )


# ---------------- VERIFY OTP ----------------

@router.post("/{transaction_id}/verify-otp", response_model=TransactionResponse)
def verify_transaction_otp(
    transaction_id: int,
    data: OtpVerifyRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = user.get("uid") or str(user.get("id"))

    tx = db.query(Transaction).filter(
        Transaction.id == transaction_id, Transaction.user_id == user_id
    ).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if not tx.otp_required or tx.otp_verified:
        raise HTTPException(status_code=400, detail="This transaction does not need OTP verification")

    challenge = (
        db.query(OtpChallenge)
        .filter(OtpChallenge.transaction_id == tx.id, OtpChallenge.verified.is_(False))
        .order_by(OtpChallenge.created_at.desc())
        .first()
    )
    if not challenge:
        raise HTTPException(status_code=400, detail="No pending OTP challenge for this transaction")

    challenge.attempts += 1
    db.commit()

    if challenge.attempts > 5:
        raise HTTPException(status_code=429, detail="Too many attempts. Transaction blocked.")

    if not verify_otp(data.code, challenge.code_hash):
        raise HTTPException(status_code=401, detail="Incorrect OTP")

    challenge.verified = True
    tx.otp_verified = True
    tx.status = TransactionStatus.INITIATED.value
    db.commit()
    db.refresh(tx)

    db.add(TransactionEvent(
        transaction_id=tx.id, stage="OTP_VERIFIED", status="OK",
        actor="Fraud Engine", message="Step-up OTP verified. Proceeding to settlement.",
    ))
    db.commit()

    settlement_queue.enqueue(run_settlement, tx.id)

    return TransactionResponse(
        id=tx.id, amount=tx.amount, is_fraud=tx.is_fraud, risk=tx.risk,
        status=tx.status, otp_required=tx.otp_required,
        payee_name=tx.payee_name, payee_verified=tx.payee_verified,
    )


# ---------------- LIVE TIMELINE ----------------

@router.get("/{transaction_id}/timeline", response_model=list[TransactionEventOut])
def transaction_timeline(
    transaction_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = user.get("uid") or str(user.get("id"))
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if tx.user_id != user_id and user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Not authorized to view this transaction")

    events = (
        db.query(TransactionEvent)
        .filter(TransactionEvent.transaction_id == transaction_id)
        .order_by(TransactionEvent.created_at.asc())
        .all()
    )
    return [
        TransactionEventOut(
            stage=e.stage, status=e.status, actor=e.actor,
            message=e.message, created_at=e.created_at.isoformat(),
        )
        for e in events
    ]


# ---------------- USER TRANSACTIONS ----------------

@router.get("/my")
def my_transactions(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = user.get("uid") or str(user.get("id"))
    return db.query(Transaction).filter(
        Transaction.user_id == user_id
    ).order_by(Transaction.created_at.desc()).all()


# ---------------- OWNER: ALL TRANSACTIONS ----------------

@router.get("/all")
def all_transactions(
    user=Depends(owner_only),
    db: Session = Depends(get_db),
):
    return db.query(Transaction).order_by(Transaction.created_at.desc()).all()
