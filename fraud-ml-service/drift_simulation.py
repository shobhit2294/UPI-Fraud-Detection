"""Chronological fraud-pattern-change simulation; outputs are explicitly simulated."""

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from fraud_pipeline import MODEL_FEATURES, add_behavioral_features, evaluate_at_threshold, make_models, chronological_split


def main() -> None:
    path = Path(__file__).parent.parent / "backend/ml/Bank_Transaction_Fraud_Detection.csv"
    data = add_behavioral_features(pd.read_csv(path))
    train, _, test = chronological_split(data)
    model = make_models()["random_forest"]
    fit_train = train.iloc[::math.ceil(len(train) / 20000)]
    model.fit(fit_train[MODEL_FEATURES], fit_train["Is_Fraud"])
    shifted = test.copy()
    # Simulation only: a later population has more new-device and high-amount events.
    shifted["new_device_activity"] = 1.0
    shifted["amount_vs_user_mean"] = shifted["amount_vs_user_mean"] * 1.5
    scores = model.predict_proba(shifted[MODEL_FEATURES])[:, 1]
    result = {
        "simulation": True,
        "scenario": "later-period new-device and amount uplift; labels are unchanged",
        "feature_shift": {"new_device_activity_mean": float(shifted["new_device_activity"].mean()), "amount_vs_user_mean_mean": float(shifted["amount_vs_user_mean"].mean())},
        "performance_on_simulated_shift": evaluate_at_threshold(test["Is_Fraud"].to_numpy(), scores, 0.60),
        "retrain_when": ["PSI or another drift metric exceeds an agreed threshold for two periods", "PR-AUC or recall falls below the fraud-risk SLO", "new device/payment behavior is materially different from training data"],
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
