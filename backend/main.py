from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.db import Base, engine
from database.seed import seed_payees
from auth.models import User
from models.transaction import Transaction, TransactionEvent, Payee, OtpChallenge

from auth.routes import router as auth_router
from routes.transaction_routes import router as transaction_router
from routes.analytics_routes import router as analytics_router
from routes.payee_routes import router as payee_router

from config import CORS_ORIGINS

app = FastAPI(title="UPI Fraud Detection API")


# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------- DB TABLE CREATE + SEED ----------------
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    seed_payees()


# ---------------- ROUTERS ----------------
app.include_router(auth_router)
app.include_router(transaction_router)
app.include_router(analytics_router)
app.include_router(payee_router)


@app.get("/health")
def health():
    return {"status": "ok"}
