import hashlib
import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from passlib.context import CryptContext

from auth.models import User
from utils.jwt import create_access_token

pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto"
)

OTP_TTL_SECONDS = 300
_otp_store: dict[str, dict[str, object]] = {}


def normalize_phone(phone: str) -> str:
    value = "".join(character for character in phone.strip() if character.isdigit() or character == "+")
    if value.startswith("00"):
        value = "+" + value[2:]
    if not value.startswith("+"):
        value = "+91" + value
    digits = value[1:]
    if not digits.isdigit() or not 8 <= len(digits) <= 15:
        raise ValueError("Enter a valid phone number with country code")
    return "+" + digits


def request_phone_otp(phone: str) -> dict[str, object]:
    normalized = normalize_phone(phone)
    code = f"{secrets.randbelow(1_000_000):06d}"
    _otp_store[normalized] = {
        "hash": hashlib.sha256(code.encode()).hexdigest(),
        "expires_at": datetime.utcnow() + timedelta(seconds=OTP_TTL_SECONDS),
        "attempts": 0,
    }
    return {"phone": normalized, "code": code, "expires_in_seconds": OTP_TTL_SECONDS}


def verify_phone_otp(db: Session, phone: str, code: str):
    normalized = normalize_phone(phone)
    record = _otp_store.get(normalized)
    if not record or datetime.utcnow() > record["expires_at"]:
        return None
    record["attempts"] = int(record["attempts"]) + 1
    if int(record["attempts"]) > 5 or not secrets.compare_digest(
        str(record["hash"]), hashlib.sha256(code.encode()).hexdigest()
    ):
        return None
    _otp_store.pop(normalized, None)
    user = db.query(User).filter(User.phone == normalized).first()
    if not user:
        user = User(phone=normalized, role="user", is_active=True)
        db.add(user)
        db.commit()
        db.refresh(user)
    if not user.is_active:
        return None
    return {
        "access_token": create_access_token({"id": user.id, "phone": normalized, "role": user.role}),
        "token_type": "bearer",
        "role": user.role,
        "phone": normalized,
    }


def login_user(db: Session, phone: str, password: str):
    user = db.query(User).filter(User.phone == phone).first()

    if not user:
        return None

    if not pwd_context.verify(password, user.password):
        return None

    token = create_access_token({
        "id": user.id,
        "role": user.role
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role
    }
