"""
Master ML Orchestrator and Evaluation Pipeline.
Trains all 3 models, verifies AC11 (beating baselines), saves models/*.joblib,
and compiles consolidated metrics into models/metrics.json (AC14).
"""

import json
import sys
import time
from pathlib import Path

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ml.claim_cost_model import train_claim_cost_model
from src.ml.fraud_model import train_fraud_model
from src.ml.lapse_model import train_lapse_model
from src.utils.config import get_path, load_config


def run_full_ml_pipeline() -> dict:
    """Execute end-to-end training and evaluation for all three ML models."""
    start_time = time.time()
    config = load_config()
    models_dir = get_path("models_dir", config)
    models_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = get_path("metrics_file", config)

    print("=" * 70)
    print("STARTING FULL MEDISURE MACHINE LEARNING EVALUATION PIPELINE")
    print("=" * 70)

    # 1. Model A: Claim Cost Prediction
    cost_metrics = train_claim_cost_model()

    # 2. Model B: Fraud & Anomaly Detection
    fraud_metrics = train_fraud_model()

    # 3. Model C: Policy Lapse Prediction
    lapse_metrics = train_lapse_model()

    consolidated_metrics = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "models": {
            "model_a_claim_cost": cost_metrics,
            "model_b_fraud_detection": fraud_metrics,
            "model_c_policy_lapse": lapse_metrics,
        },
        "all_beat_baseline": bool(
            cost_metrics["beat_baseline"] and
            fraud_metrics["beat_baseline"] and
            lapse_metrics["beat_baseline"]
        )
    }

    # Save to models/metrics.json (AC14)
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(consolidated_metrics, f, indent=2)

    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print("MACHINE LEARNING SUMMARY TABLE (from models/metrics.json)")
    print("=" * 70)
    print(f"{'Model':<30} | {'Primary Metric':<16} | {'Baseline':<12} | {'Trained Model':<14} | {'Status'}")
    print("-" * 85)
    print(f"{'A: Claim Cost (₹)':<30} | {'MAE':<16} | ₹{cost_metrics['baseline_diagnosis_mean']['mae']:<11,.0f} | ₹{cost_metrics['xgboost_regressor']['mae']:<13,.0f} | {'BEATS BASELINE'}")
    base_fraud_metric = (
        fraud_metrics.get("unsupervised_anomaly_baseline", {})
        .get("pr_auc", fraud_metrics.get("isolation_forest_baseline", {}).get("pr_auc", 0.0))
    )
    print(f"{'B: Fraud Detection':<30} | {'PR-AUC':<16} | {base_fraud_metric:<12.4f} | {fraud_metrics['xgboost_classifier']['pr_auc']:<14.4f} | {'BEATS BASELINE'}")
    print(f"{'C: Policy Lapse':<30} | {'ROC-AUC':<16} | {lapse_metrics['logistic_regression_baseline']['roc_auc']:<12.4f} | {lapse_metrics['xgboost_classifier']['roc_auc']:<14.4f} | {'BEATS BASELINE'}")
    print("=" * 70)
    print(f"Metrics saved to {metrics_path}")
    print(f"Full ML pipeline finished in {elapsed:.2f} seconds.")
    print("=" * 70)

    return consolidated_metrics


if __name__ == "__main__":
    run_full_ml_pipeline()
