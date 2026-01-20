from fastapi import FastAPI
import joblib
import numpy as np
import os
from datetime import datetime

from database import SessionLocal, engine, Base
from models import Transaction

# -----------------------------------
# App
# -----------------------------------
app = FastAPI(title="UPI Fraud Detection API")

# create tables
Base.metadata.create_all(bind=engine)

# -----------------------------------
# Load ML model
# -----------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(
    BASE_DIR,
    "model",
    "fraud_model.pkl"
)


if not os.path.exists(MODEL_PATH):
    raise RuntimeError("❌ fraud_model.pkl not found.")

model = joblib.load(MODEL_PATH)

# -----------------------------------
# Root API
# -----------------------------------
@app.get("/")
def root():
    return {"status": "Fraud Detection API running"}

# -----------------------------------
# Encoding maps
# -----------------------------------
device_map = {
    "Android": 0,
    "iOS": 1,
    "Web": 2
}

location_map = {
    "Delhi": 0,
    "Mumbai": 1,
    "Bangalore": 2,
    "Pune": 3,
    "Chennai": 4
}

# -----------------------------------
# Prediction API
# -----------------------------------
@app.post("/predict")
def predict(data: dict):

    device = device_map.get(data["device_type"], 0)
    location = location_map.get(data["location"], 0)

    features = np.array([[
        data["transaction_id"],
        data["amount"],
        device,
        location
    ]])

    prediction = int(model.predict(features)[0])
    probability = float(model.predict_proba(features)[0][1])

    risk_score = round(probability * 100, 2)

    db = SessionLocal()

    txn = Transaction(
        transaction_id=data["transaction_id"],
        amount=data["amount"],
        device_type=data["device_type"],
        location=data["location"],
        fraud=bool(prediction),
        risk_score=risk_score,
        created_at=datetime.utcnow()
    )

    db.add(txn)
    db.commit()
    db.close()

    return {
        "fraud": bool(prediction),
        "risk_score": risk_score
    }

# -----------------------------------
# Transaction history API
# -----------------------------------
@app.get("/transactions")
def get_transactions():
    db = SessionLocal()

    records = db.query(Transaction).order_by(
        Transaction.created_at.desc()
    ).all()

    db.close()

    return [
        {
            "transaction_id": t.transaction_id,
            "amount": t.amount,
            "device_type": t.device_type,
            "location": t.location,
            "fraud": t.fraud,
            "risk_score": t.risk_score,
            "created_at": t.created_at
        }
        for t in records
    ]
