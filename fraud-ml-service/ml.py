from fastapi import FastAPI
from pydantic import BaseModel
import random

app = FastAPI()

class Transaction(BaseModel):
    user_id: str
    amount: float
    hour: int
    device_new: bool
    location_changed: bool

@app.post("/ml-score")
def ml_score(tx: Transaction):
    """
    ML probability simulator
    Banks never expose real model directly
    """

    score = 0

    if tx.amount > 30000:
        score += 15

    if tx.device_new:
        score += 10

    if tx.location_changed:
        score += 10

    if tx.hour >= 0 and tx.hour <= 5:
        score += 5

    # small randomness like real ML models
    score += random.randint(0, 5)

    return {
        "ml_score": score
    }

