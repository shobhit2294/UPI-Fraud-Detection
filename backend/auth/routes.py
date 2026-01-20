from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.db import SessionLocal
from auth.schemas import LoginRequest, LoginResponse
from auth.controller import login_user

router = APIRouter(prefix="/auth", tags=["Auth"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    result = login_user(db, data.phone, data.password)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return result
