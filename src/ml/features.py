"""
Feature engineering pipelines and data preparation for MediSure ML models.
Implements strict time-based splits and leakage-free transformations.
"""

import numpy as np
import pandas as pd

from src.utils.io import get_duckdb_connection

# Forbidden columns that must NEVER enter Model A (Claim Cost) to prevent target leakage
FORBIDDEN_CLAIM_COST_COLUMNS = {
    "paid_amount", "approved_amount", "patient_paid_amount",
    "claim_status", "rejection_reason", "settlement_tat_days",
    "claim_settled_date", "is_fraud_flag"
}


def load_claim_cost_dataset() -> pd.DataFrame:
    """Load claims dataset joined with member, policy, and provider attributes."""
    con = get_duckdb_connection(read_only=True)
    df = con.execute("""
        SELECT
            c.claim_id,
            c.admission_date,
            c.claim_submitted_date,
            c.claim_type,
            c.is_emergency,
            c.is_planned,
            c.paid_amount,
            m.age_at_enrollment,
            m.gender,
            m.region,
            m.city_tier,
            m.occupation_category,
            m.income_band,
            m.bmi,
            m.smoker_flag,
            m.has_diabetes,
            m.has_hypertension,
            m.has_cardiac_history,
            m.pre_existing_conditions_count,
            p.plan_type,
            p.plan_tier,
            p.sum_insured,
            p.deductible,
            p.co_pay_pct,
            p.sales_channel,
            prv.hospital_tier,
            prv.network_status,
            d.diagnosis_category,
            d.severity_level
        FROM fact_claims c
        JOIN dim_member m ON c.member_id = m.member_id
        JOIN dim_policy p ON c.policy_id = p.policy_id
        JOIN dim_provider prv ON c.provider_id = prv.provider_id
        JOIN dim_diagnosis d ON c.diagnosis_id = d.diagnosis_id
        WHERE c.paid_amount > 0  -- Train/evaluate on paid hospitalizations
    """).df()
    con.close()
    return df


def load_fraud_dataset() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load claims for fraud detection and compute provider fraud rate proxy
    STRICTLY on training data (2021-2024) to avoid data leakage.
    """
    con = get_duckdb_connection(read_only=True)
    df = con.execute("""
        SELECT
            c.claim_id,
            c.member_id,
            c.provider_id,
            c.diagnosis_id,
            c.admission_date,
            c.claim_submitted_date,
            c.length_of_stay,
            c.icu_days,
            c.billed_amount,
            c.is_fraud_flag,
            EXTRACT(isodow FROM c.admission_date) AS day_of_week,
            d.diagnosis_category,
            d.typical_los_days,
            d.typical_cost_min,
            d.typical_cost_max,
            prv.hospital_tier,
            prv.network_status
        FROM fact_claims c
        JOIN dim_diagnosis d ON c.diagnosis_id = d.diagnosis_id
        JOIN dim_provider prv ON c.provider_id = prv.provider_id
    """).df()
    con.close()

    df["admission_date"] = pd.to_datetime(df["admission_date"])
    df["is_weekend"] = df["day_of_week"].isin([6, 7]).astype(int)
    df["is_round_billed"] = (df["billed_amount"] % 10000.0 == 0).astype(int)
    df["icu_ratio"] = df["icu_days"] / np.maximum(df["length_of_stay"], 1)
    df["los_ratio"] = df["length_of_stay"] / np.maximum(df["typical_los_days"], 1)

    # Compute diagnosis benchmark ratio
    dx_mid = (df["typical_cost_min"] + df["typical_cost_max"]) / 2.0
    df["billed_to_dx_ratio"] = df["billed_amount"] / dx_mid

    # Split train (2021-2024) vs test (2025)
    train_mask = df["admission_date"] < "2025-01-01"
    train_df = df[train_mask].copy()
    test_df = df[~train_mask].copy()

    # Provider fraud rate computed STRICTLY on training data
    prv_train_fraud = train_df.groupby("provider_id")["is_fraud_flag"].agg(["count", "mean"]).reset_index()
    prv_train_fraud.columns = ["provider_id", "prv_train_claims", "prv_historical_fraud_rate"]
    global_fraud_mean = float(train_df["is_fraud_flag"].mean())

    # Merge provider proxy back into train and test
    train_df = train_df.merge(prv_train_fraud[["provider_id", "prv_historical_fraud_rate"]], on="provider_id", how="left")
    train_df["prv_historical_fraud_rate"] = train_df["prv_historical_fraud_rate"].fillna(global_fraud_mean)

    test_df = test_df.merge(prv_train_fraud[["provider_id", "prv_historical_fraud_rate"]], on="provider_id", how="left")
    test_df["prv_historical_fraud_rate"] = test_df["prv_historical_fraud_rate"].fillna(global_fraud_mean)

    return train_df, test_df


def load_lapse_dataset() -> pd.DataFrame:
    """Load renewals dataset joined with policy and claims experience."""
    con = get_duckdb_connection(read_only=True)
    df = con.execute("""
        WITH claim_exp AS (
            SELECT
                policy_id,
                COUNT(claim_id) AS policy_claim_count,
                COUNT(CASE WHEN claim_status = 'Rejected' THEN 1 END) AS rejected_claims_count,
                COALESCE(AVG(settlement_tat_days), 0.0) AS avg_tat_experienced
            FROM fact_claims
            GROUP BY policy_id
        ),
        prem_exp AS (
            SELECT
                policy_id,
                COUNT(CASE WHEN payment_status = 'Late' THEN 1 END) AS late_payment_count,
                COALESCE(AVG(days_late), 0.0) AS avg_days_late
            FROM fact_premiums
            GROUP BY policy_id
        )
        SELECT
            r.renewal_id,
            r.policy_id,
            r.renewal_due_date,
            r.renewed_flag,
            r.premium_change_pct,
            p.plan_type,
            p.plan_tier,
            p.sales_channel,
            p.annual_premium,
            p.renewal_count AS policy_tenure,
            COALESCE(ce.policy_claim_count, 0) AS policy_claim_count,
            COALESCE(ce.rejected_claims_count, 0) AS rejected_claims_count,
            COALESCE(ce.avg_tat_experienced, 0.0) AS avg_tat_experienced,
            COALESCE(pe.late_payment_count, 0) AS late_payment_count,
            COALESCE(pe.avg_days_late, 0.0) AS avg_days_late
        FROM fact_renewals r
        JOIN dim_policy p ON r.policy_id = p.policy_id
        LEFT JOIN claim_exp ce ON r.policy_id = ce.policy_id
        LEFT JOIN prem_exp pe ON r.policy_id = pe.policy_id
    """).df()
    con.close()
    return df
