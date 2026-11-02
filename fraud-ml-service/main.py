"""FastAPI real-time fraud scoring service with safe defaults."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from threading import Lock
from typing import Any

import joblib
import pandas as pd
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

try:
    import redis
except ImportError:  # optional for local development
    redis = None

from fraud_pipeline import MODEL_FEATURES, shap_contributions

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("fraud-ml")
ROOT = Path(__file__).parent
MODEL_VERSION = os.getenv("MODEL_VERSION", "fraud-rf-v2")
THRESHOLD = float(os.getenv("FRAUD_RISK_THRESHOLD", "0.60"))
COUNTER_TTL_SECONDS = int(os.getenv("COUNTER_TTL_SECONDS", "900"))
_memory_cache: dict[str, dict[str, Any]] = {}
_idempotency_cache: dict[str, dict[str, Any]] = {}
_memory_lock = Lock()


def _load_bundle() -> dict[str, Any]:
    bundle_path = ROOT / "model_bundle.pkl"
    if bundle_path.exists():
        return joblib.load(bundle_path)
    model = joblib.load(ROOT / "fraud_model.pkl")
    encoders = joblib.load(ROOT / "encoders.pkl")
    return {"model": model, "encoders": encoders, "version": "legacy-rf-v1", "threshold": 0.60, "legacy": True}


bundle = _load_bundle()
model = bundle["model"]
app = FastAPI(title="Fraud ML Service", version=MODEL_VERSION)
redis_client = None
if redis and os.getenv("REDIS_URL"):
    redis_client = redis.Redis.from_url(os.environ["REDIS_URL"], socket_timeout=0.05, decode_responses=True)


class PredictRequest(BaseModel):
    transaction_id: str | None = Field(default=None, max_length=128)
    user_id: str = Field(default="anonymous", min_length=1, max_length=128)
    Transaction_Amount: float = Field(gt=0, le=100_000_000)
    Account_Balance: float = Field(ge=0, le=1_000_000_000)
    City: str = Field(min_length=1, max_length=128)
    Device_Type: str = Field(min_length=1, max_length=128)
    Transaction_Type: str = Field(min_length=1, max_length=128)
    Age: int = Field(ge=13, le=120)
    event_time: str | None = None
    new_device: bool | None = None
    transaction_velocity_10m: int | None = Field(default=None, ge=0, le=10000)
    amount_vs_user_mean: float | None = Field(default=None, ge=0, le=100000)
    seconds_since_last_transaction: float | None = Field(default=None, ge=-1, le=31_536_000)


def _counter_features(payload: PredictRequest) -> dict[str, float]:
    key = f"fraud:velocity:{payload.user_id}"
    try:
        if redis_client:
            count = int(redis_client.incr(key))
            redis_client.expire(key, COUNTER_TTL_SECONDS)
            return {"transaction_velocity_10m": float(max(count - 1, 0))}
    except Exception as exc:
        logger.warning("redis_feature_store_unavailable", extra={"error": str(exc)})
    now = time.time()
    with _memory_lock:
        timestamps = [t for t in _memory_cache.get(key, {}).get("timestamps", []) if now - t < 600]
        count = len(timestamps)
        timestamps.append(now)
        _memory_cache[key] = {"timestamps": timestamps}
    return {"transaction_velocity_10m": float(count)}


def _features(payload: PredictRequest) -> pd.DataFrame:
    if bundle.get("legacy"):
        row = pd.DataFrame([{
            "Transaction_Amount": payload.Transaction_Amount,
            "Account_Balance": payload.Account_Balance,
            "City": payload.City,
            "Device_Type": payload.Device_Type,
            "Transaction_Type": payload.Transaction_Type,
            "Age": payload.Age,
        }])
        for column, encoder in bundle["encoders"].items():
            value = str(row.at[0, column])
            row.at[0, column] = encoder.transform([value])[0] if value in encoder.classes_ else 0
        return row
    velocity = payload.transaction_velocity_10m
    if velocity is None:
        velocity = _counter_features(payload)["transaction_velocity_10m"]
    parsed_time = pd.to_datetime(payload.event_time, errors="coerce") if payload.event_time else None
    row = {
        "Transaction_Amount": payload.Transaction_Amount,
        "Account_Balance": payload.Account_Balance,
        "Age": payload.Age,
        "City": payload.City,
        "Device_Type": payload.Device_Type,
        "Transaction_Type": payload.Transaction_Type,
        "hour": parsed_time.hour if parsed_time is not None and not pd.isna(parsed_time) else 0,
        "day_of_week": parsed_time.dayofweek if parsed_time is not None and not pd.isna(parsed_time) else 0,
        "balance_after_transaction_ratio": payload.Account_Balance / max(payload.Transaction_Amount, 1.0),
        "transaction_velocity_10m": velocity,
        "amount_vs_user_mean": payload.amount_vs_user_mean if payload.amount_vs_user_mean is not None else 1.0,
        "amount_zscore_user": 0.0,
        "new_device_activity": float(bool(payload.new_device)),
        "seconds_since_last_transaction": payload.seconds_since_last_transaction if payload.seconds_since_last_transaction is not None else -1.0,
    }
    return pd.DataFrame([row], columns=MODEL_FEATURES)


def _factors(features: pd.DataFrame, score: float, threshold: float) -> list[dict[str, Any]]:
    factors = []
    row = features.iloc[0]
    if row["transaction_velocity_10m"] >= 3:
        factors.append({"feature": "transaction_velocity_10m", "value": row["transaction_velocity_10m"], "direction": "increases_risk"})
    if row["amount_vs_user_mean"] >= 2:
        factors.append({"feature": "amount_vs_user_mean", "value": row["amount_vs_user_mean"], "direction": "increases_risk"})
    if row["new_device_activity"]:
        factors.append({"feature": "new_device_activity", "value": True, "direction": "increases_risk"})
    if not factors:
        factors.append({
            "feature": "model_score_threshold",
            "value": {"score": round(score, 6), "threshold": threshold},
            "direction": "increases_risk" if score >= threshold else "decreases_risk",
        })
    return factors


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model_version": str(bundle.get("version", MODEL_VERSION))}


@app.post("/predict")
def predict(payload: PredictRequest, idempotency_key: str | None = Header(default=None)) -> dict[str, Any]:
    started = time.perf_counter()
    cache_key = idempotency_key or payload.transaction_id
    digest = hashlib.sha256(cache_key.encode()).hexdigest() if cache_key else None
    if digest and digest in _idempotency_cache:
        return _idempotency_cache[digest]
    if digest and redis_client:
        try:
            cached = redis_client.get(f"fraud:idempotency:{digest}")
            if cached:
                return json.loads(cached)
        except Exception:
            pass
    try:
        features = _features(payload)
        score = float(model.predict_proba(features)[0][1])
        threshold = float(bundle.get("threshold", THRESHOLD))
        response = {
            "risk_score": round(score, 6),
            "risk_percent": round(score * 100, 2),
            "is_fraud": score >= threshold,
            "decision": "block_or_review" if score >= threshold else "allow",
            "contributing_factors": _factors(features, score, threshold),
            "shap_contributions": shap_contributions(model, features) if not bundle.get("legacy") else [],
            "model_version": str(bundle.get("version", MODEL_VERSION)),
            "recommended_next_action": "step_up_authentication" if score >= threshold else "continue",
            "inference_latency_ms": round((time.perf_counter() - started) * 1000, 3),
        }
    except Exception as exc:
        logger.exception("prediction_failed", extra={"error": str(exc)})
        raise HTTPException(status_code=503, detail={"decision": "block_or_review", "reason": "risk_engine_unavailable"}) from exc
    if digest and redis_client:
        try:
            redis_client.setex(f"fraud:idempotency:{digest}", 300, json.dumps(response))
        except Exception:
            pass
    if digest:
        _idempotency_cache[digest] = response
    logger.info("prediction_complete", extra={"model_version": response["model_version"], "latency_ms": response["inference_latency_ms"]})
    return response
