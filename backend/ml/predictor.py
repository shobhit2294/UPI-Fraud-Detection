"""
Client for the fraud-ml-service microservice.

The model itself no longer lives in the backend process -- it's owned by
fraud-ml-service so it can be scaled/deployed/retrained independently
(this is the Juspay-style separation of "orchestrator" from "risk engine").
"""

import requests
from config import FRAUD_ML_SERVICE_URL


def predict_fraud(payload: dict) -> tuple[bool, int, dict]:
    try:
        resp = requests.post(
            f"{FRAUD_ML_SERVICE_URL}/predict",
            json=payload,
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        risk = data.get("risk_percent", data.get("risk", 100))
        return bool(data["is_fraud"]), int(round(float(risk))), data
    except requests.RequestException as e:
        # Fail safe: if the risk engine is unreachable, treat as
        # high-risk/needs-review rather than silently approving.
        print("fraud-ml-service unreachable:", str(e))
        return True, 100, {
            "decision": "block_or_review",
            "recommended_next_action": "manual_review",
            "model_version": "unavailable",
            "contributing_factors": [{"feature": "risk_engine_unavailable", "direction": "increases_risk"}],
        }
