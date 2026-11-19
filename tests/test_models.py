"""
Unit tests for Machine Learning models, feature leakage, and performance baselines.
Validates Acceptance Criteria AC11, AC12, AC13, and AC14.
"""

import json

from src.ml.features import FORBIDDEN_CLAIM_COST_COLUMNS, load_claim_cost_dataset
from src.utils.config import get_path
from src.utils.io import read_parquet


def test_no_target_leakage():
    """AC13: Ensure forbidden columns are completely excluded from the Model A feature matrix."""
    df = load_claim_cost_dataset()
    feature_columns = set(df.columns) - {"claim_id", "admission_date", "claim_submitted_date", "paid_amount"}

    leakage_found = feature_columns.intersection(FORBIDDEN_CLAIM_COST_COLUMNS)
    assert not leakage_found, f"Target leakage detected! Excluded columns present in features: {leakage_found}"


def test_models_exist_and_beat_baselines():
    """AC11 & AC14: Verify models/metrics.json exists, artifacts exist, and all models beat baselines."""
    metrics_path = get_path("metrics_file")
    assert metrics_path.exists(), "models/metrics.json does not exist. Run python src/ml/evaluate.py first."

    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    models_data = metrics.get("models", {})
    assert "model_a_claim_cost" in models_data, "Model A metrics missing"
    assert "model_b_fraud_detection" in models_data, "Model B metrics missing"
    assert "model_c_policy_lapse" in models_data, "Model C metrics missing"

    # Model A check
    mA = models_data["model_a_claim_cost"]
    assert mA["beat_baseline"], f"Model A did not beat baseline: {mA}"
    assert mA["xgboost_regressor"]["mae"] < mA["baseline_diagnosis_mean"]["mae"]

    # Model B check (AC12)
    mB = models_data["model_b_fraud_detection"]
    assert mB["beat_baseline"], f"Model B did not beat baseline: {mB}"
    assert "optimal_threshold_analysis" in mB
    assert mB["optimal_threshold_analysis"]["net_financial_savings_inr"] > 0
    assert mB["primary_metric"] == "PR-AUC"

    # Model C check
    mC = models_data["model_c_policy_lapse"]
    assert mC["beat_baseline"], f"Model C did not beat baseline: {mC}"
    assert mC["xgboost_classifier"]["roc_auc"] > mC["logistic_regression_baseline"]["roc_auc"]

    # Overall flag
    assert metrics.get("all_beat_baseline", False) is True


def test_model_artifacts_and_lapse_scores():
    """AC14: Verify all .joblib artifacts and lapse_scores.parquet exist and are valid."""
    models_dir = get_path("models_dir")
    for artifact in ["claim_cost_model.joblib", "fraud_model.joblib", "lapse_model.joblib"]:
        p = models_dir / artifact
        assert p.exists(), f"Artifact {artifact} not found in {models_dir}"

    processed_dir = get_path("processed_dir")
    lapse_scores_path = processed_dir / "lapse_scores.parquet"
    assert lapse_scores_path.exists(), f"lapse_scores.parquet not found in {processed_dir}"

    scores_df = read_parquet(lapse_scores_path)
    assert not scores_df.empty
    assert "predicted_lapse_probability" in scores_df.columns
    assert "risk_tier" in scores_df.columns
    assert (scores_df["predicted_lapse_probability"] >= 0.0).all()
    assert (scores_df["predicted_lapse_probability"] <= 1.0).all()
