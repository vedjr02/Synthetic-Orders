"""
Train XGBoost ETA regressor and SLA breach classifier; serialize with joblib.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, mean_absolute_error, roc_auc_score
from sklearn.model_selection import train_test_split

try:
    from xgboost import XGBClassifier, XGBRegressor

    USE_XGBOOST = True
except Exception:
    from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

    USE_XGBOOST = False
    print("XGBoost unavailable (install libomp on macOS: brew install libomp). Using HistGradientBoosting.")

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "thane_orders.csv"
MODELS_DIR = ROOT / "models"

FEATURE_COLS = [
    "hour_of_day",
    "day_of_week",
    "weather_severity",
    "distance_m",
    "active_rider_count",
    "base_travel_time_min",
]

WEATHER_FACTOR = {"Clear": 1.0, "Rain": 1.15, "Heavy Rain": 1.35}
BASE_SURGE = 1.0
RANDOM_SEED = 42


def compute_surge_multiplier(sla_risk: float, weather: str) -> float:
    """Surge = Base * (1 + SLA_Breach_Risk) * Weather_Factor."""
    wf = WEATHER_FACTOR.get(weather, 1.0)
    return round(BASE_SURGE * (1.0 + sla_risk) * wf, 3)


def main() -> None:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Run data_pipeline.py first. Missing: {DATA_PATH}")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(DATA_PATH)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    X = df[FEATURE_COLS].astype(float)
    y_eta = df["actual_eta_min"].astype(float)
    y_sla = df["sla_breach"].astype(int)

    X_train, X_test, y_eta_train, y_eta_test, y_sla_train, y_sla_test = train_test_split(
        X, y_eta, y_sla, test_size=0.2, random_state=RANDOM_SEED, stratify=y_sla
    )

    print("Training ETA regressor …")
    if USE_XGBOOST:
        eta_model = XGBRegressor(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.08,
            subsample=0.85,
            colsample_bytree=0.85,
            random_state=RANDOM_SEED,
            n_jobs=-1,
        )
    else:
        eta_model = HistGradientBoostingRegressor(
            max_iter=300,
            max_depth=6,
            learning_rate=0.08,
            random_state=RANDOM_SEED,
        )
    eta_model.fit(X_train, y_eta_train)
    eta_pred = eta_model.predict(X_test)
    eta_mae = mean_absolute_error(y_eta_test, eta_pred)
    print(f"  ETA MAE: {eta_mae:.2f} min")

    print("Training SLA breach classifier …")
    if USE_XGBOOST:
        sla_model = XGBClassifier(
            n_estimators=250,
            max_depth=5,
            learning_rate=0.1,
            subsample=0.9,
            colsample_bytree=0.9,
            eval_metric="logloss",
            random_state=RANDOM_SEED,
            n_jobs=-1,
        )
    else:
        sla_model = HistGradientBoostingClassifier(
            max_iter=250,
            max_depth=5,
            learning_rate=0.1,
            random_state=RANDOM_SEED,
        )
    sla_model.fit(X_train, y_sla_train)
    sla_proba = sla_model.predict_proba(X_test)[:, 1]
    sla_pred = (sla_proba >= 0.5).astype(int)
    sla_acc = accuracy_score(y_sla_test, sla_pred)
    sla_auc = roc_auc_score(y_sla_test, sla_proba)
    print(f"  SLA accuracy: {sla_acc:.3f} | AUC: {sla_auc:.3f}")

    # Attach surge to holdout sample for sanity check
    holdout = df.iloc[X_test.index].copy()
    holdout["sla_risk_pred"] = sla_proba
    holdout["surge_multiplier"] = holdout.apply(
        lambda r: compute_surge_multiplier(r["sla_risk_pred"], r["weather_condition"]), axis=1
    )
    print(f"  Mean surge (holdout): {holdout['surge_multiplier'].mean():.3f}")

    joblib.dump(eta_model, MODELS_DIR / "eta_regressor.joblib")
    joblib.dump(sla_model, MODELS_DIR / "sla_classifier.joblib")

    meta = {
        "feature_columns": FEATURE_COLS,
        "eta_mae_min": round(float(eta_mae), 4),
        "sla_accuracy": round(float(sla_acc), 4),
        "sla_auc": round(float(sla_auc), 4),
        "weather_factor": WEATHER_FACTOR,
        "base_surge": BASE_SURGE,
        "surge_formula": "Base * (1 + SLA_Breach_Risk) * Weather_Factor",
        "model_backend": "xgboost" if USE_XGBOOST else "sklearn_hist_gradient_boosting",
    }
    (MODELS_DIR / "model_meta.json").write_text(json.dumps(meta, indent=2))

    print(f"Models saved → {MODELS_DIR}")


if __name__ == "__main__":
    main()
