from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.db import Base, engine
from auth.models import User
from models.transaction import Transaction
from auth.routes import router as auth_router
from routes.transaction_routes import router as transaction_router
from routes.analytics_routes import router as analytics_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(auth_router)
app.include_router(transaction_router)
app.include_router(analytics_router)
