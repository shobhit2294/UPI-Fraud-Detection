# UPI Fraud Detection System

A demo payment-and-fraud-detection platform modeled on how real UPI apps
(PhonePe/GPay/Paytm) and payment orchestrators (Juspay/PayU) work: payee
verification before you pay, risk-based OTP step-up, geolocation as a fraud
signal, and a live multi-hop settlement timeline that mirrors the real
bank → PSP → aggregator → merchant chain — including the "debited but not
confirmed" stuck state that real UPI failures produce.

## Architecture

```
Browser (login.html, dashboards)
     │
     ▼
 backend (FastAPI)  ──HTTP──►  fraud-ml-service (FastAPI + calibrated threshold)
     │
     ├──► Postgres (users, transactions, payees, OTP challenges, events)
     │
     └──► Redis queue ──► reconciliation-worker
                              (simulates BANK_ACK → PSP_PROCESSING →
                               AGGREGATOR_PROCESSING → SETTLED / FAILED /
                               STUCK_PENDING_RECONCILIATION)
```

Services:
- **backend** — the payment orchestrator API (auth, payee verification, transaction creation, OTP, timeline)
- **fraud-ml-service** — standalone risk-scoring microservice (owns the model, independently deployable)
- **reconciliation-worker** — background worker that simulates the multi-hop settlement chain
- **redis** — job queue between backend and reconciliation-worker
- **postgres** — source of truth (sqlite is used automatically for quick local dev without Docker)

## Fraud model workflow

The model pipeline is in `fraud-ml-service/`. Run `python train_model.py` from that directory to create a leakage-safe `model_bundle.pkl` and `evaluation_report.json`. It compares Logistic Regression and Random Forest, uses chronological 60/20/20 train/validation/test splits, selects the threshold on validation only, and reports precision, recall, F1, PR-AUC, false-positive rate, confusion matrices, threshold trade-offs, and p50/p95/p99 inference latency. XGBoost/LightGBM can be added as optional candidates when installed; the core pipeline has no dependency on either.

Behavioral features are causal: 10-minute transaction velocity, amount versus prior user history, user amount z-score, new-device activity, and seconds since the prior transaction. This supplied dataset has one row per customer, so those history features are neutral for the training rows; repeated-user production traffic is the intended use case.

`POST /predict` accepts an optional `Idempotency-Key` header and returns `risk_score`, `contributing_factors`, `model_version`, and `recommended_next_action`. Redis stores only short-lived velocity counters and idempotency responses. If Redis is unavailable, counters fall back to process-local memory; if model scoring fails, the service returns a 503 with a review/block-safe decision.

Run `python drift_simulation.py` to print an explicitly labeled chronological fraud-pattern-change simulation and retraining signals. Simulated metrics must not be represented as production performance.

## Running with Docker (recommended)

1. Copy the env template and fill in a real secret:
   ```bash
   cd backend
   cp .env.example .env
   python3 -c "import secrets; print(secrets.token_hex(32))"   # paste into JWT_SECRET_KEY
   ```
2. Put your real Firebase service-account key at `backend/firebase/firebase-key.json`
   (never commit this file — it's already in `.gitignore`).
3. From the project root:
   ```bash
   export JWT_SECRET_KEY=<same value you put in backend/.env>
   docker compose up --build
   ```
4. Backend: http://localhost:8000 · fraud-ml-service: http://localhost:9100 · Postgres: localhost:5433 · Redis: localhost:6379
5. Open `frontend/login.html` in a browser (or serve it with any static server, e.g. `python3 -m http.server 5500` from `frontend/`).

## Running locally without Docker (matches the original dev setup)

```bash
cd ~/PROJECT/UPI-Fraud-Detection-System
source venv/bin/activate

# terminal 1 -- fraud ML microservice
cd fraud-ml-service
pip install -r requirements.txt
uvicorn main:app --reload --port 9100

# terminal 2 -- redis (needs redis-server installed)
redis-server

# terminal 3 -- reconciliation worker
cd backend
pip install -r requirements.txt
cp .env.example .env   # fill in JWT_SECRET_KEY at minimum
rq worker --url redis://localhost:6379/0 settlement

# terminal 4 -- backend API
cd backend
uvicorn main:app --reload
```

Without `DATABASE_URL` set, the backend automatically falls back to a local
`sqlite:///./database.db` file, so this works without Postgres too.

## Making a user an "owner"

Roles are stored in the `users` table. After a user has logged in once via
Firebase (which auto-creates their row), promote them manually:

```sql
UPDATE users SET role = 'owner' WHERE email = 'you@example.com';
```

Or for local-login test users, set `role='owner'` when creating the row.

## What's simulated vs. real

This project **cannot** move real money, verify real bank accounts, or
access NPCI's actual mapper service — those require bank/NPCI membership.
What it does simulate faithfully:
- **Payee verification**: a seeded demo directory (`backend/database/seed.py`)
  stands in for NPCI's real name-lookup service.
- **Multi-hop settlement**: the reconciliation-worker introduces realistic
  delay and a configurable chance of landing in `STUCK_PENDING_RECONCILIATION`
  — the same "bank says success, receiver says nothing" state real disputed
  UPI transactions can end up in. In real life, that requires a bank/NPCI
  dispute, not a code fix.
- **OTP step-up**: a real one-time password, generated server-side and
  hashed at rest — the only demo-only part is that (since there's no SMS
  gateway here) the code is echoed back in the API response when
  `DEMO_MODE=true`, clearly labeled as such. A real deployment would send it
  by SMS/push and never return it in a response.
- **Geolocation**: real browser geolocation (with an explicit permission
  prompt), used as one additional fraud signal alongside amount/city/device.

## Security notes

- `JWT_SECRET_KEY` and the Firebase service-account key are both required
  environment/file inputs now — there are no hardcoded secrets in source.
- `/transactions/all` and both `/analytics/*` endpoints require the `owner`
  role.
- `.gitignore` excludes `.env`, `firebase-key.json`, and local `.db` files.
  If `firebase-key.json` was ever pushed to a public repo, rotate it in the
  Firebase console regardless of what's in `.gitignore` now.

## API summary

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/auth/login` | none | Local phone/password login (demo) |
| POST | `/auth/request-otp` | none | Generate a phone OTP; demo mode returns it for automatic UI fill |
| POST | `/auth/verify-otp` | none | Verify the phone OTP and issue a JWT |
| POST | `/auth/firebase-login` | Firebase ID token | Real login path |
| POST | `/payees/verify` | user | Look up a VPA before paying |
| POST | `/transactions/` | user | Create + risk-score a transaction |
| POST | `/transactions/{id}/verify-otp` | user | Step-up OTP verification |
| GET | `/transactions/{id}/timeline` | owner or transaction's user | Live settlement hops |
| GET | `/transactions/my` | user | Your own transactions |
| GET | `/transactions/all` | owner | All transactions |
| GET | `/analytics/summary`, `/analytics/daily` | owner | Aggregate fraud stats |

### Phone OTP login

The frontend login screen now uses a phone number and OTP. With the default
local `DEMO_MODE=true`, clicking **Send OTP** calls `/auth/request-otp`, fills
the returned demo code automatically, and verifies it through
`/auth/verify-otp`. This is real-time application behavior but not real SMS.

For production, set `DEMO_MODE=false` and connect the same screen to Firebase
Phone Auth or an SMS provider such as Twilio. Never return `demo_otp` from a
production API.
