"""
Model A: Claim Cost Prediction (Regression).
Predicts expected paid amount in INR at claim submission time.
Compares Ridge vs Gradient Boosting against global and diagnosis-group baselines.
"""

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBRegressor

from src.ml.features import FORBIDDEN_CLAIM_COST_COLUMNS, load_claim_cost_dataset
from src.utils.config import get_path


def calculate_smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate Symmetric Mean Absolute Percentage Error (sMAPE)."""
    denom = (np.abs(y_true) + np.abs(y_pred)) / 2.0
    return float(np.mean(np.where(denom == 0, 0, np.abs(y_pred - y_true) / denom)) * 100.0)


def train_claim_cost_model() -> dict:
    """Train, evaluate, and serialize Model A."""
    print("=" * 60)
    print("Training Model A: Claim Cost Prediction (Regression)...")
    print("=" * 60)

    df = load_claim_cost_dataset()
    df["admission_date"] = pd.to_datetime(df["admission_date"])

    # Strict time-based split: Train 2021-2024, Test 2025
    train_mask = df["admission_date"] < "2025-01-01"
    train_df = df[train_mask].copy()
    test_df = df[~train_mask].copy()

    y_train_raw = train_df["paid_amount"].to_numpy()
    y_test_raw = test_df["paid_amount"].to_numpy()

    # Log1p target
    y_train = np.log1p(y_train_raw)
    y_test = np.log1p(y_test_raw)

    # Feature definitions
    cat_features = [
        "gender", "region", "occupation_category", "income_band",
        "plan_type", "plan_tier", "sales_channel", "hospital_tier",
        "network_status", "claim_type", "diagnosis_category"
    ]
    num_features = [
        "age_at_enrollment", "city_tier", "bmi", "smoker_flag",
        "has_diabetes", "has_hypertension", "has_cardiac_history",
        "pre_existing_conditions_count", "sum_insured", "deductible",
        "co_pay_pct", "is_emergency", "is_planned", "severity_level"
    ]

    # Verify no target leakage in features
    all_features = set(cat_features + num_features)
    leakage = all_features.intersection(FORBIDDEN_CLAIM_COST_COLUMNS)
    assert not leakage, f"Target leakage detected in features: {leakage}"

    X_train = train_df[cat_features + num_features]
    X_test = test_df[cat_features + num_features]

    # Preprocessing pipeline
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), num_features),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_features)
        ]
    )

    # Baseline 1: Global Mean
    global_mean_val = np.mean(y_train)
    y_pred_base_global = np.expm1(np.full_like(y_test, global_mean_val))
    mae_base_global = mean_absolute_error(y_test_raw, y_pred_base_global)
    rmse_base_global = np.sqrt(mean_squared_error(y_test_raw, y_pred_base_global))

    # Baseline 2: Diagnosis-Category Mean
    dx_means = train_df.groupby("diagnosis_category")["paid_amount"].mean().to_dict()
    y_pred_base_dx = test_df["diagnosis_category"].map(dx_means).fillna(np.mean(y_train_raw)).to_numpy()
    mae_base_dx = mean_absolute_error(y_test_raw, y_pred_base_dx)
    rmse_base_dx = np.sqrt(mean_squared_error(y_test_raw, y_pred_base_dx))

    print(f"Baseline (Global Mean)   -> MAE: INR {mae_base_global:,.2f}, RMSE: INR {rmse_base_global:,.2f}")
    print(f"Baseline (Diagnosis Mean) -> MAE: INR {mae_base_dx:,.2f}, RMSE: INR {rmse_base_dx:,.2f}")

    # Model 1: Ridge Regression
    ridge_pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", Ridge(alpha=10.0, random_state=42))
    ])
    ridge_pipeline.fit(X_train, y_train)
    y_pred_ridge_log = ridge_pipeline.predict(X_test)
    y_pred_ridge = np.expm1(y_pred_ridge_log)
    mae_ridge = mean_absolute_error(y_test_raw, y_pred_ridge)
    rmse_ridge = np.sqrt(mean_squared_error(y_test_raw, y_pred_ridge))
    r2_ridge = r2_score(y_test_raw, y_pred_ridge)
    print(f"Ridge Regression         -> MAE: INR {mae_ridge:,.2f}, RMSE: INR {rmse_ridge:,.2f}, R2: {r2_ridge:.4f}")

    # Model 2: Gradient Boosting (XGBoost)
    xgb_pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", XGBRegressor(
            n_estimators=150,
            learning_rate=0.08,
            max_depth=5,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=4
        ))
    ])
    xgb_pipeline.fit(X_train, y_train)
    y_pred_xgb_log = xgb_pipeline.predict(X_test)
    y_pred_xgb = np.expm1(y_pred_xgb_log)
    mae_xgb = mean_absolute_error(y_test_raw, y_pred_xgb)
    rmse_xgb = np.sqrt(mean_squared_error(y_test_raw, y_pred_xgb))
    r2_xgb = r2_score(y_test_raw, y_pred_xgb)
    smape_xgb = calculate_smape(y_test_raw, y_pred_xgb)
    print(f"XGBoost Regressor        -> MAE: INR {mae_xgb:,.2f}, RMSE: INR {rmse_xgb:,.2f}, R2: {r2_xgb:.4f}, sMAPE: {smape_xgb:.2f}%")

    # Decile calibration
    calib_df = pd.DataFrame({"actual": y_test_raw, "predicted": y_pred_xgb})
    calib_df["decile"] = pd.qcut(calib_df["predicted"], 10, labels=False) + 1
    decile_summary = calib_df.groupby("decile").agg(
        actual_mean=("actual", "mean"),
        predicted_mean=("predicted", "mean")
    ).to_dict(orient="index")

    # Serialize best model
    models_dir = get_path("models_dir")
    models_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(xgb_pipeline, models_dir / "claim_cost_model.joblib")
    print(f"Saved claim_cost_model.joblib to {models_dir}")

    metrics = {
        "model_name": "Claim Cost Prediction (XGBoost Regressor)",
        "train_rows": len(train_df),
        "test_rows": len(test_df),
        "split": "Time-based (Train < 2025, Test >= 2025)",
        "baseline_global_mean": {"mae": round(mae_base_global, 2), "rmse": round(rmse_base_global, 2)},
        "baseline_diagnosis_mean": {"mae": round(mae_base_dx, 2), "rmse": round(rmse_base_dx, 2)},
        "ridge_regression": {"mae": round(mae_ridge, 2), "rmse": round(rmse_ridge, 2), "r2": round(r2_ridge, 4)},
        "xgboost_regressor": {
            "mae": round(mae_xgb, 2),
            "rmse": round(rmse_xgb, 2),
            "r2": round(r2_xgb, 4),
            "smape_pct": round(smape_xgb, 2)
        },
        "beat_baseline": bool(mae_xgb < mae_base_dx and rmse_xgb < rmse_base_dx),
        "decile_calibration": decile_summary
    }

    return metrics


if __name__ == "__main__":
    train_claim_cost_model()
