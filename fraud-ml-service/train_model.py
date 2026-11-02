"""Train and evaluate fraud models with chronological, leakage-safe splits.

Run from this directory: ``python train_model.py --data ../backend/ml/Bank_Transaction_Fraud_Detection.csv``.
The JSON report is intentionally saved next to the model so threshold decisions and
simulated results remain auditable.
"""

import argparse
import json
import math
from pathlib import Path

import joblib
import pandas as pd

from fraud_pipeline import MODEL_FEATURES, add_behavioral_features, chronological_split, make_models, measure_latency, threshold_table, evaluate_at_threshold


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="../backend/ml/Bank_Transaction_Fraud_Detection.csv")
    parser.add_argument("--output", default=".")
    parser.add_argument("--max-train-rows", type=int, default=20000, help="Cap fit rows for memory-safe local training; use 0 for all rows.")
    args = parser.parse_args()
    output = Path(args.output)
    raw = pd.read_csv(args.data)
    data = add_behavioral_features(raw)
    train, validation, test = chronological_split(data)
    fit_train = train if args.max_train_rows <= 0 or len(train) <= args.max_train_rows else train.iloc[::math.ceil(len(train) / args.max_train_rows)]
    x_train, y_train = fit_train[MODEL_FEATURES], fit_train["Is_Fraud"].astype(int)
    x_validation, y_validation = validation[MODEL_FEATURES], validation["Is_Fraud"].astype(int).to_numpy()
    x_test, y_test = test[MODEL_FEATURES], test["Is_Fraud"].astype(int).to_numpy()

    report = {"simulation": False, "split": {"train_available": len(train), "train_fitted": len(fit_train), "validation": len(validation), "test": len(test)}, "models": {}}
    candidates = make_models()
    for name, model in candidates.items():
        model.fit(x_train, y_train)
        validation_scores = model.predict_proba(x_validation)[:, 1]
        test_scores = model.predict_proba(x_test)[:, 1]
        # Select a threshold on validation only. This favors F1 while retaining a
        # full operating-point table for the fraud/legitimate trade-off.
        candidates_thresholds = [0.20, 0.35, 0.50, 0.65, 0.80]
        best = max(candidates_thresholds, key=lambda t: evaluate_at_threshold(y_validation, validation_scores, t)["f1"])
        report["models"][name] = {
            "validation": evaluate_at_threshold(y_validation, validation_scores, best),
            "test": evaluate_at_threshold(y_test, test_scores, best),
            "thresholds": threshold_table(y_test, test_scores),
            "inference_latency_ms": measure_latency(model, x_test.iloc[:1]),
        }
        if name == "random_forest":
            joblib.dump({"model": model, "version": "fraud-rf-v2", "threshold": best, "features": MODEL_FEATURES}, output / "model_bundle.pkl")

    (output / "evaluation_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
