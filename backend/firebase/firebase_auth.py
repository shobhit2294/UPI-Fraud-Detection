import firebase_admin
from firebase_admin import credentials, auth
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer

from config import FIREBASE_CREDENTIALS_PATH

# initialize firebase only once
if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)

security = HTTPBearer()


def verify_firebase_user(token=Depends(security)):
    try:
        decoded = auth.verify_id_token(
            token.credentials,
            check_revoked=True
        )
        return decoded
    except Exception as e:
        print("Firebase auth error:", str(e))
        raise HTTPException(
            status_code=401,
            detail="Invalid Firebase token"
        )
