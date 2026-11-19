"""
Model C: Policy Lapse Prediction (Classification).
Predicts probability of policy churn (renewed_flag == 0) at renewal time.
Computes ROC-AUC, PR-AUC, lift/gain analysis, and retention targeting simulation.
Exports scored dataset to data/processed/lapse_scores.parquet.
"""

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from src.ml.features import load_lapse_dataset
from src.utils.config import get_path
from src.utils.io import save_parquet


def train_lapse_model() -> dict:
    """Train, evaluate, and serialize Model C and export scored lapse table."""
    print("=" * 60)
    print("Training Model C: Policy Lapse Prediction (Classification)...")
    print("=" * 60)

    df = load_lapse_dataset()
    df["renewal_due_date"] = pd.to_datetime(df["renewal_due_date"])

    # Target: 1 if lapsed (renewed_flag == 0), 0 if renewed
    df["target_lapse"] = (df["renewed_flag"] == 0).astype(int)

    # Time-based split: Train < 2025, Test >= 2025
    train_mask = df["renewal_due_date"] < "2025-01-01"
    train_df = df[train_mask].copy()
    test_df = df[~train_mask].copy()

    feature_cols = [
        "premium_change_pct", "policy_claim_count", "rejected_claims_count",
        "avg_tat_experienced", "late_payment_count", "avg_days_late",
        "policy_tenure", "annual_premium", "plan_type", "plan_tier", "sales_channel"
    ]
    cat_cols = ["plan_type", "plan_tier", "sales_channel"]
    num_cols = [c for c in feature_cols if c not in cat_cols]

    X_train = train_df[feature_cols]
    y_train = train_df["target_lapse"].to_numpy()

    X_test = test_df[feature_cols]
    y_test = test_df["target_lapse"].to_numpy()

    print(f"Lapse Training Prevalence: {np.mean(y_train) * 100:.2f}% (Persistence: {100 - np.mean(y_train)*100:.2f}%)")

    # Preprocessing
    preprocessor = ColumnTransformer([
        ("num", StandardScaler(), num_cols),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_cols)
    ])

    # 1. Baseline: Logistic Regression
    lr_pipeline = Pipeline([
        ("prep", preprocessor),
        ("clf", LogisticRegression(max_iter=500, random_state=42))
    ])
    lr_pipeline.fit(X_train, y_train)
    y_pred_lr = lr_pipeline.predict_proba(X_test)[:, 1]
    roc_auc_lr = roc_auc_score(y_test, y_pred_lr)
    pr_auc_lr = average_precision_score(y_test, y_pred_lr)
    print(f"Logistic Regression Baseline -> ROC-AUC: {roc_auc_lr:.4f}, PR-AUC: {pr_auc_lr:.4f}")

    # 2. XGBoost Classifier
    xgb_pipeline = Pipeline([
        ("prep", preprocessor),
        ("clf", XGBClassifier(
            n_estimators=150,
            learning_rate=0.08,
            max_depth=4,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=4,
            eval_metric="logloss"
        ))
    ])
    xgb_pipeline.fit(X_train, y_train)
    y_pred_xgb = xgb_pipeline.predict_proba(X_test)[:, 1]
    roc_auc_xgb = roc_auc_score(y_test, y_pred_xgb)
    pr_auc_xgb = average_precision_score(y_test, y_pred_xgb)
    print(f"XGBoost Classifier           -> ROC-AUC: {roc_auc_xgb:.4f}, PR-AUC: {pr_auc_xgb:.4f}")

    # 3. Retention Targeting Simulation (Lift / Gain analysis)
    scored_test = test_df[["policy_id", "renewal_due_date", "plan_tier", "sales_channel", "annual_premium"]].copy()
    scored_test["actual_lapse"] = y_test
    scored_test["predicted_lapse_probability"] = y_pred_xgb

    # Assign risk tier
    scored_test["risk_tier"] = pd.qcut(
        scored_test["predicted_lapse_probability"],
        q=[0.0, 0.70, 0.90, 1.0],
        labels=["Low", "Medium", "High"]
    )

    # Sort descending by lapse risk
    scored_sorted = scored_test.sort_values(by="predicted_lapse_probability", ascending=False).reset_index(drop=True)
    n_total = len(scored_sorted)
    n_top20 = int(0.20 * n_total)
    total_lapses = int(sum(y_test))
    lapses_in_top20 = int(scored_sorted.iloc[:n_top20]["actual_lapse"].sum())
    top20_capture_rate = (lapses_in_top20 / total_lapses) * 100.0
    lift_top20 = (lapses_in_top20 / n_top20) / (total_lapses / n_total)

    print("Top 20% Retention Targeting Simulation:")
    print(f" - Lapses captured in top 20% outreach: {lapses_in_top20:,} of {total_lapses:,} ({top20_capture_rate:.2f}%)")
    print(f" - Lift in Top 20% Decile: {lift_top20:.2f}x over random outreach")

    # Decile Lift Table
    scored_sorted["decile"] = pd.qcut(scored_sorted.index, 10, labels=range(1, 11))
    decile_lift = scored_sorted.groupby("decile", observed=False).agg(
        policies=("policy_id", "count"),
        lapses=("actual_lapse", "sum"),
        mean_pred_prob=("predicted_lapse_probability", "mean")
    ).reset_index()
    decile_lift["lapse_rate"] = decile_lift["lapses"] / decile_lift["policies"] * 100.0
    decile_lift["cum_lapses"] = decile_lift["lapses"].cumsum()
    decile_lift["cum_gain_pct"] = decile_lift["cum_lapses"] / total_lapses * 100.0

    # Save scored table to data/processed/lapse_scores.parquet
    processed_dir = get_path("processed_dir")
    save_parquet(scored_test, processed_dir / "lapse_scores.parquet")
    print(f"Saved lapse_scores.parquet to {processed_dir}")

    # Serialize best model
    models_dir = get_path("models_dir")
    joblib.dump(xgb_pipeline, models_dir / "lapse_model.joblib")
    print(f"Saved lapse_model.joblib to {models_dir}")

    metrics = {
        "model_name": "Policy Lapse Prediction (XGBoost Classifier)",
        "train_rows": len(train_df),
        "test_rows": len(test_df),
        "target_class": "target_lapse (1 = Lapsed, 0 = Renewed)",
        "lapse_prevalence_pct": round(np.mean(y_train) * 100.0, 2),
        "logistic_regression_baseline": {"roc_auc": round(roc_auc_lr, 4), "pr_auc": round(pr_auc_lr, 4)},
        "xgboost_classifier": {"roc_auc": round(roc_auc_xgb, 4), "pr_auc": round(pr_auc_xgb, 4)},
        "beat_baseline": bool(roc_auc_xgb > roc_auc_lr and pr_auc_xgb > pr_auc_lr),
        "retention_targeting_simulation": {
            "top_percentile_targeted": 20.0,
            "total_lapses_in_test": total_lapses,
            "lapses_captured_in_top_20": lapses_in_top20,
            "capture_rate_pct": round(top20_capture_rate, 2),
            "lift_multiplier": round(lift_top20, 2)
        },
        "decile_gain_curve": decile_lift.to_dict(orient="records")
    }

    return metrics


if __name__ == "__main__":
    train_lapse_model()
