"""Leakage-safe feature engineering, model comparison, and evaluation utilities."""

from __future__ import annotations

from time import perf_counter
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


BEHAVIORAL_COLUMNS = [
    "transaction_velocity_10m",
    "amount_vs_user_mean",
    "amount_zscore_user",
    "new_device_activity",
    "seconds_since_last_transaction",
]
NUMERIC_COLUMNS = [
    "Transaction_Amount",
    "Account_Balance",
    "Age",
    "hour",
    "day_of_week",
    "balance_after_transaction_ratio",
    *BEHAVIORAL_COLUMNS,
]
CATEGORICAL_COLUMNS = ["City", "Device_Type", "Transaction_Type"]
MODEL_FEATURES = NUMERIC_COLUMNS + CATEGORICAL_COLUMNS


def _timestamp(frame: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(
        frame["Transaction_Date"].astype(str) + " " + frame["Transaction_Time"].astype(str),
        dayfirst=True,
        errors="coerce",
    )


def add_behavioral_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Build features using only transactions earlier than the current row."""
    data = frame.copy()
    data["_event_time"] = _timestamp(data)
    data = data.sort_values(["_event_time"], kind="mergesort").reset_index(drop=True)
    users: dict[str, dict[str, Any]] = {}
    values: list[dict[str, float]] = []

    customer_ids = data.get("Customer_ID", pd.Series("__anonymous__", index=data.index)).fillna("__anonymous__")
    devices = data.get("Device_Type", pd.Series("unknown", index=data.index)).fillna("unknown")
    amounts = data["Transaction_Amount"].fillna(0.0)
    for user_id_value, device_value, amount_value, now in zip(customer_ids, devices, amounts, data["_event_time"]):
        user_id = str(user_id_value)
        device = str(device_value)
        amount = float(amount_value)
        state = users.setdefault(user_id, {"times": [], "amounts": [], "devices": set()})
        recent = [t for t in state["times"] if (now - t).total_seconds() <= 600]
        prior_amounts = state["amounts"]
        mean = float(np.mean(prior_amounts)) if prior_amounts else amount
        std = float(np.std(prior_amounts)) if len(prior_amounts) > 1 else 0.0
        previous = state["times"][-1] if state["times"] else None
        values.append(
            {
                "transaction_velocity_10m": float(len(recent)),
                "amount_vs_user_mean": amount / max(mean, 1.0),
                "amount_zscore_user": (amount - mean) / max(std, 1.0) if prior_amounts else 0.0,
                "new_device_activity": float(bool(state["devices"]) and device not in state["devices"]),
                "seconds_since_last_transaction": (
                    float((now - previous).total_seconds()) if previous is not None else -1.0
                ),
            }
        )
        state["times"].append(now)
        state["amounts"].append(amount)
        state["devices"].add(device)

    features = pd.DataFrame(values, index=data.index)
    data = pd.concat([data, features], axis=1)
    data["hour"] = data["_event_time"].dt.hour.fillna(0)
    data["day_of_week"] = data["_event_time"].dt.dayofweek.fillna(0)
    data["balance_after_transaction_ratio"] = data["Account_Balance"] / np.maximum(
        data["Transaction_Amount"], 1.0
    )
    return data


def make_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        [
            ("numeric", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), NUMERIC_COLUMNS),
            ("categorical", Pipeline([("impute", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]), CATEGORICAL_COLUMNS),
        ]
    )


def make_models() -> dict[str, Pipeline]:
    models = {
        "logistic_regression": Pipeline([
            ("features", make_preprocessor()),
            ("model", LogisticRegression(class_weight="balanced", max_iter=500, solver="liblinear", random_state=42)),
        ]),
        "random_forest": Pipeline([
            ("features", make_preprocessor()),
            ("model", RandomForestClassifier(n_estimators=50, max_depth=14, class_weight="balanced_subsample", min_samples_leaf=2, n_jobs=1, random_state=42)),
        ]),
    }
    # Optional challenger: the core service remains scikit-learn-only when the
    # package is not installed in a constrained deployment image.
    try:
        from xgboost import XGBClassifier

        models["xgboost"] = Pipeline([
            ("features", make_preprocessor()),
            ("model", XGBClassifier(
                n_estimators=250, max_depth=6, learning_rate=0.08,
                subsample=0.85, colsample_bytree=0.85, scale_pos_weight=5,
                eval_metric="logloss", n_jobs=-1, random_state=42,
            )),
        ])
    except Exception:
        pass
    return models


def chronological_split(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ordered = data.sort_values("_event_time", kind="mergesort")
    first = int(len(ordered) * 0.60)
    second = int(len(ordered) * 0.80)
    return ordered.iloc[:first], ordered.iloc[first:second], ordered.iloc[second:]


def evaluate_at_threshold(y_true: np.ndarray, scores: np.ndarray, threshold: float) -> dict[str, Any]:
    predicted = scores >= threshold
    tn, fp, fn, tp = confusion_matrix(y_true, predicted, labels=[0, 1]).ravel()
    return {
        "threshold": threshold,
        "precision": float(precision_score(y_true, predicted, zero_division=0)),
        "recall": float(recall_score(y_true, predicted, zero_division=0)),
        "f1": float(f1_score(y_true, predicted, zero_division=0)),
        "pr_auc": float(average_precision_score(y_true, scores)),
        "roc_auc": float(roc_auc_score(y_true, scores)),
        "false_positive_rate": float(fp / max(fp + tn, 1)),
        "confusion_matrix": [[int(tn), int(fp)], [int(fn), int(tp)]],
        "fraud_caught": int(tp),
        "legitimate_flagged": int(fp),
    }


def threshold_table(y_true: np.ndarray, scores: np.ndarray) -> list[dict[str, Any]]:
    return [evaluate_at_threshold(y_true, scores, value) for value in (0.20, 0.35, 0.50, 0.65, 0.80)]


def measure_latency(model: Pipeline, sample: pd.DataFrame, iterations: int = 100) -> dict[str, float]:
    durations = []
    for _ in range(iterations):
        started = perf_counter()
        model.predict_proba(sample)
        durations.append((perf_counter() - started) * 1000)
    return {f"p{p}": float(np.percentile(durations, p)) for p in (50, 95, 99)}


def shap_contributions(model: Pipeline, sample: pd.DataFrame, limit: int = 5) -> list[dict[str, Any]]:
    """Return optional SHAP contributions; empty means the optional package is absent."""
    try:
        import shap

        transformed = model.named_steps["features"].transform(sample)
        estimator = model.named_steps["model"]
        explainer = shap.TreeExplainer(estimator)
        values = explainer.shap_values(transformed)
        values = values[1] if isinstance(values, list) else values
        names = model.named_steps["features"].get_feature_names_out()
        ranked = np.argsort(np.abs(values[0]))[::-1][:limit]
        return [{"feature": str(names[i]), "contribution": float(values[0][i])} for i in ranked]
    except Exception:
        return []
