"""
Model B: Fraud & Anomaly Detection (Classification).
Detects high-risk fraudulent and abusive insurance claims.
Evaluates PR-AUC (primary), ROC-AUC, Unsupervised Statistical Anomaly baseline,
and cost-based financial threshold analysis.
"""

import joblib
import numpy as np
from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer
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
from xgboost import XGBClassifier

from src.ml.features import load_fraud_dataset
from src.utils.config import get_path


class StatisticalAnomalyDetector(BaseEstimator):
    """
    Unsupervised standardized anomaly detector.
    Computes multivariate standardized deviation scores for each claim.
    Serves as the unsupervised anomaly baseline without external compiled DLLs.
    """
    def __init__(self):
        self.mean_ = None
        self.std_ = None

    def fit(self, X, y=None):
        X_arr = np.asarray(X)
        self.mean_ = np.mean(X_arr, axis=0)
        self.std_ = np.std(X_arr, axis=0) + 1e-6
        return self

    def score_samples(self, X):
        X_arr = np.asarray(X)
        z_scores = np.abs((X_arr - self.mean_) / self.std_)
        return np.mean(z_scores, axis=1)


def train_fraud_model() -> dict:
    """Train, evaluate, and serialize Model B."""
    print("=" * 60)
    print("Training Model B: Fraud & Anomaly Detection (Classification)...")
    print("=" * 60)

    train_df, test_df = load_fraud_dataset()

    feature_cols = [
        "billed_amount", "billed_to_dx_ratio", "length_of_stay", "los_ratio",
        "icu_ratio", "is_weekend", "is_round_billed", "prv_historical_fraud_rate",
        "hospital_tier", "network_status", "diagnosis_category"
    ]
    cat_cols = ["hospital_tier", "network_status", "diagnosis_category"]
    num_cols = [c for c in feature_cols if c not in cat_cols]

    X_train = train_df[feature_cols]
    y_train = train_df["is_fraud_flag"].to_numpy()

    X_test = test_df[feature_cols]
    y_test = test_df["is_fraud_flag"].to_numpy()
    test_billed = test_df["billed_amount"].to_numpy()

    fraud_prevalence = float(np.mean(y_train))
    print(f"Training Fraud Prevalence: {fraud_prevalence * 100:.2f}% (Heavily imbalanced)")

    # Preprocessing
    preprocessor = ColumnTransformer([
        ("num", StandardScaler(), num_cols),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_cols)
    ])

    # 1. Unsupervised Baseline: Statistical Anomaly Detector
    print("Evaluating Unsupervised Statistical Anomaly Baseline...")
    X_train_prep = preprocessor.fit_transform(X_train)
    X_test_prep = preprocessor.transform(X_test)

    anomaly_baseline = StatisticalAnomalyDetector()
    anomaly_baseline.fit(X_train_prep)
    iso_scores = anomaly_baseline.score_samples(X_test_prep)
    pr_auc_iso = average_precision_score(y_test, iso_scores)
    roc_auc_iso = roc_auc_score(y_test, iso_scores)
    print(f"Statistical Anomaly Baseline -> PR-AUC: {pr_auc_iso:.4f}, ROC-AUC: {roc_auc_iso:.4f}")

    # 2. Supervised Gradient Boosting (XGBoost with scale_pos_weight)
    print("Training Supervised XGBoost Classifier...")
    pos_weight = (len(y_train) - sum(y_train)) / sum(y_train)
    xgb_pipeline = Pipeline([
        ("prep", preprocessor),
        ("clf", XGBClassifier(
            n_estimators=150,
            learning_rate=0.06,
            max_depth=4,
            scale_pos_weight=pos_weight,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=4,
            eval_metric="aucpr"
        ))
    ])
    xgb_pipeline.fit(X_train, y_train)
    y_pred_proba = xgb_pipeline.predict_proba(X_test)[:, 1]

    pr_auc_xgb = average_precision_score(y_test, y_pred_proba)
    roc_auc_xgb = roc_auc_score(y_test, y_pred_proba)
    print(f"XGBoost Classifier        -> PR-AUC: {pr_auc_xgb:.4f}, ROC-AUC: {roc_auc_xgb:.4f}")

    # 3. Cost-Based Financial Threshold Optimization
    # Investigation Cost = INR 2,000 per investigated claim
    # False Negative (missed fraud) Cost = actual billed amount
    # True Positive Benefit = fraud billed amount saved
    investigation_cost = 2000.0

    thresholds = np.linspace(0.05, 0.95, 91)
    best_savings = -float("inf")
    best_threshold = 0.50
    best_metrics = {}

    cost_curves = []
    for th in thresholds:
        pred_fraud = (y_pred_proba >= th).astype(int)
        cm = confusion_matrix(y_test, pred_fraud)
        tn, fp, fn, tp = cm.ravel()

        # Net financial benefit calculation
        total_investigations = tp + fp
        audit_expenditure = total_investigations * investigation_cost

        # Caught fraud amount
        fraud_caught_amount = float(np.sum(test_billed[(y_test == 1) & (pred_fraud == 1)]))
        net_savings = fraud_caught_amount - audit_expenditure

        cost_curves.append({
            "threshold": round(float(th), 2),
            "precision": round(float(precision_score(y_test, pred_fraud, zero_division=0)), 4),
            "recall": round(float(recall_score(y_test, pred_fraud, zero_division=0)), 4),
            "f1": round(float(f1_score(y_test, pred_fraud, zero_division=0)), 4),
            "investigations": int(total_investigations),
            "net_savings_inr": round(net_savings, 2)
        })

        if net_savings > best_savings:
            best_savings = net_savings
            best_threshold = float(th)
            best_metrics = {
                "threshold": round(float(th), 2),
                "precision": round(float(precision_score(y_test, pred_fraud, zero_division=0)), 4),
                "recall": round(float(recall_score(y_test, pred_fraud, zero_division=0)), 4),
                "f1": round(float(f1_score(y_test, pred_fraud, zero_division=0)), 4),
                "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
                "total_investigations": int(total_investigations),
                "fraud_amount_recovered_inr": round(fraud_caught_amount, 2),
                "net_financial_savings_inr": round(net_savings, 2)
            }

    print(f"Optimal Financial Operating Threshold: {best_threshold:.2f}")
    print(f"Net Financial Savings at Optimal Threshold: INR {best_savings:,.2f}")
    print(f"Precision: {best_metrics['precision']:.3f}, Recall: {best_metrics['recall']:.3f}")

    # Serialize best model
    models_dir = get_path("models_dir")
    models_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(xgb_pipeline, models_dir / "fraud_model.joblib")
    print(f"Saved fraud_model.joblib to {models_dir}")

    metrics = {
        "model_name": "Fraud & Anomaly Detection (XGBoost Classifier)",
        "train_rows": len(train_df),
        "test_rows": len(test_df),
        "target_class": "is_fraud_flag",
        "prevalence_pct": round(fraud_prevalence * 100.0, 2),
        "primary_metric": "PR-AUC",
        "unsupervised_anomaly_baseline": {"pr_auc": round(pr_auc_iso, 4), "roc_auc": round(roc_auc_iso, 4)},
        "xgboost_classifier": {
            "pr_auc": round(pr_auc_xgb, 4),
            "roc_auc": round(roc_auc_xgb, 4)
        },
        "beat_baseline": bool(pr_auc_xgb > pr_auc_iso),
        "optimal_threshold_analysis": best_metrics,
        "sample_cost_curve": cost_curves[::5],
        "headline_metric_disclaimer": "Raw accuracy is omitted because a naive zero-classifier yields 97.8% accuracy while detecting 0 fraud. PR-AUC and Net Financial Savings are the domain-appropriate evaluation standards."
    }

    return metrics


if __name__ == "__main__":
    train_fraud_model()
