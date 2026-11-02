"""
Central configuration for the backend service.

Everything that used to be hardcoded (JWT secret, DB URL, thresholds) now
comes from environment variables, loaded from a .env file in local/dev
and from real environment variables (docker-compose / your platform's
secret manager) in deployed environments.

NEVER commit a real .env file. Use .env.example as the template.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


# ---------------- JWT ----------------
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    # Loud, obvious fallback for local dev only -- never used in prod because
    # docker-compose / deployment configs are required to set JWT_SECRET_KEY.
    JWT_SECRET_KEY = "dev-only-insecure-secret-change-me"

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# ---------------- Database ----------------
# Defaults to local sqlite so `uvicorn main:app --reload` still works without
# docker. docker-compose sets DATABASE_URL to the Postgres connection string.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database.db")

# ---------------- Redis / job queue ----------------
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SETTLEMENT_QUEUE_NAME = os.getenv("SETTLEMENT_QUEUE_NAME", "settlement")

# ---------------- fraud-ml microservice ----------------
FRAUD_ML_SERVICE_URL = os.getenv("FRAUD_ML_SERVICE_URL", "http://localhost:9100")

# ---------------- Risk thresholds ----------------
FRAUD_RISK_THRESHOLD = int(os.getenv("FRAUD_RISK_THRESHOLD", "60"))
OTP_REQUIRED_RISK_THRESHOLD = int(os.getenv("OTP_REQUIRED_RISK_THRESHOLD", "40"))

# ---------------- CORS ----------------
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5500,http://127.0.0.1:5500"
    ).split(",")
    if origin.strip()
]

# ---------------- Firebase ----------------
# Path to the service-account JSON. In docker-compose this is mounted as a
# secret file; locally it can point at backend/firebase/firebase-key.json
# (which must stay out of git -- see .gitignore).
FIREBASE_CREDENTIALS_PATH = os.getenv(
    "FIREBASE_CREDENTIALS_PATH",
    os.path.join(os.path.dirname(__file__), "firebase", "firebase-key.json"),
)

# ---------------- Reconciliation simulation ----------------
# Demo-only knobs that control how the reconciliation-worker simulates
# multi-hop settlement delay/failure, so you can see STUCK / FAILED states.
SETTLEMENT_MIN_DELAY_SECONDS = float(os.getenv("SETTLEMENT_MIN_DELAY_SECONDS", "1"))
SETTLEMENT_MAX_DELAY_SECONDS = float(os.getenv("SETTLEMENT_MAX_DELAY_SECONDS", "3"))
SETTLEMENT_STUCK_PROBABILITY = float(os.getenv("SETTLEMENT_STUCK_PROBABILITY", "0.12"))
SETTLEMENT_FAIL_PROBABILITY = float(os.getenv("SETTLEMENT_FAIL_PROBABILITY", "0.05"))

DEMO_MODE = _get_bool("DEMO_MODE", True)  # exposes OTP codes in API responses for demo purposes
