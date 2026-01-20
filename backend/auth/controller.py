from sqlalchemy.orm import Session
from passlib.context import CryptContext
from auth.models import User
from utils.jwt import create_access_token

pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def login_user(db: Session, phone: str, password: str):
    user = db.query(User).filter(User.phone == phone).first()

    if not user:
        return None

    if not pwd.verify(password, user.password):
        return None

    token = create_access_token({
        "id": user.id,
        "role": user.role
    })

    return {
        "token": token,
        "role": user.role
    }
