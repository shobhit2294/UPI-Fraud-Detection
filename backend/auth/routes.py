from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.db import get_db
from auth.schemas import LoginRequest, LoginResponse, RequestOtpRequest, RequestOtpResponse, VerifyOtpRequest
from auth.controller import login_user, request_phone_otp, verify_phone_otp
from auth.models import User

from firebase.firebase_auth import verify_firebase_user
from utils.jwt import create_access_token
from config import DEMO_MODE

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/request-otp", response_model=RequestOtpResponse)
def request_otp(data: RequestOtpRequest):
    try:
        result = request_phone_otp(data.phone)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "message": "OTP generated. Check your phone for the code.",
        "expires_in_seconds": result["expires_in_seconds"],
        "demo_otp": result["code"] if DEMO_MODE else None,
    }


@router.post("/verify-otp")
def verify_otp(data: VerifyOtpRequest, db: Session = Depends(get_db)):
    try:
        result = verify_phone_otp(db, data.phone, data.otp)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not result:
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")
    return result


# ---------------- LOCAL LOGIN ----------------
# (for testing / demo -- phone + password against the local users table)

@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    result = login_user(db, data.phone, data.password)

    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return result


# ---------------- FIREBASE LOGIN ----------------
# (REAL CLOUD AUTH)
#
# Role is resolved from our own `users` table, keyed by the Firebase email.
# First time a given Firebase user logs in we create a local row for them
# with role="user". To make someone an owner, update that row's role
# directly in the DB (see README).

@router.post("/firebase-login")
def firebase_login(user=Depends(verify_firebase_user), db: Session = Depends(get_db)):
    email = user.get("email")
    uid = user["uid"]

    local_user = db.query(User).filter(User.firebase_uid == uid).first()

    if not local_user and email:
        local_user = db.query(User).filter(User.email == email).first()

    if not local_user:
        local_user = User(
            email=email,
            firebase_uid=uid,
            role="user",
            is_active=True,
        )
        db.add(local_user)
        db.commit()
        db.refresh(local_user)
    elif not local_user.firebase_uid:
        # backfill uid if the row was created some other way
        local_user.firebase_uid = uid
        db.commit()

    token = create_access_token({
        "uid": uid,
        "email": email,
        "role": local_user.role,
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": local_user.role,
        "email": email,
    }
